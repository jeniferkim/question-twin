"""Prepare locally reviewed telecom question data without publishing provider text.

Run from the repository root: python -m src.data.prepare_questions --help
Only paths below gitignored data/raw/ are valid output destinations.
This module deliberately does not fabricate duplicate_group or split labels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
from io import StringIO
import json
from pathlib import Path
import re
import sys
import unicodedata

from src.data.aihub_loader import DataError, extract_candidates, read_archive
from src.data.aihub_schema import requirement_labels, source_records

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_ROOT = ROOT / "data" / "raw"
CODES_PATH = ROOT / "data" / "consult_codes.csv"
CSV_COLUMNS = ("id", "question", "category_code", "duplicate_group", "split")
REVIEW_COLUMNS = ("source_key", "question", "category_code", "status")
APPROVAL_COLUMNS = ("source_key", "approved_question")
SENSITIVE_PATTERN = re.compile(
    r"<[^>]+>|[\w.+-]+@[\w.-]+|(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)|"
    r"(?<!\d)\d{6}[- ]?\d{7}(?!\d)|(?<!\d)\d{9,}(?!\d)"
)


class PreparationError(ValueError):
    """Publicly printable error codes: never include source text or private paths."""


def private_output_path(path: Path, root: Path = ROOT) -> Path:
    target = Path(path).resolve()
    allowed = (root / "data" / "raw").resolve()
    if not target.is_relative_to(allowed) or target == allowed:
        raise PreparationError("output_must_be_under_data_raw")
    return target


def detect_archive_kind(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".zip") or name.endswith(".zip.part0"):
        return "zip"
    if name.endswith(".tar"):
        return "tar"
    raise PreparationError("unsupported_archive_suffix")


def normalize_question(question: str) -> str:
    if not isinstance(question, str):
        raise PreparationError("invalid_question")
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", question)).strip()


def read_codes(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    seen_codes: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"category_code", "aihub_category"}.issubset(reader.fieldnames or []):
            raise PreparationError("invalid_codes_schema")
        for row in reader:
            code = row.get("category_code", "")
            category = row.get("aihub_category", "")
            if not code or not category or code in seen_codes or category in mapping:
                raise PreparationError("ambiguous_category_mapping")
            seen_codes.add(code)
            mapping[category] = code
    if not mapping:
        raise PreparationError("empty_category_mapping")
    return mapping


def _csv_bytes(fields: tuple[str, ...], rows: list[dict]) -> bytes:
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(fields), lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8-sig")


def _save_once(path: Path, data: bytes, root: Path) -> None:
    target = private_output_path(path, root)
    if target.exists():
        if target.is_file() and target.read_bytes() == data:
            return  # Identical repeat execution is harmless.
        raise PreparationError("output_exists_different")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as stream:
            stream.write(data)
    except FileExistsError:
        raise PreparationError("output_exists_different") from None


def _private_key(source_id: str) -> str:
    return hashlib.sha256(b"question-twin-local-review-v1\x00" + source_id.encode("utf-8")).hexdigest()


def _load_approvals(path: Path) -> dict[str, str]:
    approved: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(APPROVAL_COLUMNS):
            raise PreparationError("invalid_approval_schema")
        for row in reader:
            key = row.get("source_key")
            question = row.get("approved_question")
            if not key or not re.fullmatch(r"[a-f0-9]{64}", key):
                raise PreparationError("invalid_approval_key")
            if key in approved:
                raise PreparationError("duplicate_approval_key")
            if question is None:
                raise PreparationError("invalid_approval_row")
            if question.strip():
                approved[key] = normalize_question(question)
    return approved


def _build_approved_rows(review_rows: list[dict], approvals: dict[str, str]) -> tuple[list[dict], dict[str, int]]:
    by_key = {row["source_key"]: row for row in review_rows}
    if set(approvals) - set(by_key):
        raise PreparationError("unknown_approval_key")
    groups: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for key, question in approvals.items():
        if (not 6 <= len(question) <= 500 or SENSITIVE_PATTERN.search(question)
                or question[0] in "=+-@" or any(ord(ch) < 32 for ch in question)):
            raise PreparationError("approved_question_needs_privacy_review")
        category = by_key[key]["category_code"]
        groups[question.casefold()].append((key, question, category))

    selected: list[tuple[int, str, str]] = []
    counts: Counter[str] = Counter()
    for group in groups.values():
        codes = {item[2] for item in group}
        if len(codes) > 1:
            counts["conflicting_category_texts"] += len(group)
            continue  # Do not guess a label for a text shared by different categories.
        group.sort(key=lambda item: item[0])
        counts["duplicate_texts_removed"] += len(group) - 1
        key, question, category = group[0]
        identifier = int(key[:14], 16)  # Stable 56-bit numeric ID, no raw source identifier.
        selected.append((identifier, question, category))

    selected.sort(key=lambda item: item[0])
    if len({item[0] for item in selected}) != len(selected):
        raise PreparationError("derived_id_collision")
    if not selected:
        raise PreparationError("no_approved_questions")
    rows = [dict(id=identifier, question=question, category_code=category,
                 duplicate_group="", split="") for identifier, question, category in selected]
    counts["approved_rows"] = len(approvals)
    counts["exported_rows"] = len(rows)
    return rows, dict(sorted(counts.items()))


def prepare(*, sources_path: Path, labels_path: Path, codes_path: Path,
            review_output: Path, report_output: Path, questions_output: Path,
            approvals_path: Path | None = None, approval_template: Path | None = None,
            root: Path = ROOT) -> dict:
    """Build a local private review queue, optionally export manually reviewed questions.

    No external calls or automatic source approval. All writes are within data/raw/.
    """
    outputs = [review_output, report_output] + ([questions_output] if approvals_path else [])
    if approval_template is not None and approvals_path is None:
        outputs.append(approval_template)
    resolved = [private_output_path(item, root) for item in outputs]
    if len(set(resolved)) != len(resolved):
        raise PreparationError("duplicate_output_path")
    # Validate existing data files before writing anything to disk.
    category_map = read_codes(codes_path)
    with Path(sources_path).open("rb") as source:
        sources = source_records(read_archive(source, detect_archive_kind(Path(sources_path))))
    with Path(labels_path).open("rb") as label:
        labels = requirement_labels(read_archive(label, detect_archive_kind(Path(labels_path))))
    batch = extract_candidates(sources, labels, category_map)
    review_rows = []
    for candidate in batch.candidates:
        question = normalize_question(candidate.question)
        csv_risk = bool(question and (question[0] in "=+-@" or any(ord(ch) < 32 for ch in question)))
        review_rows.append({"source_key": _private_key(candidate.source_id),
                            "question": "" if csv_risk else question,
                            "category_code": candidate.category_code,
                            "status": "needs_manual_review_formula_risk" if csv_risk else "needs_manual_review"})
    review_rows.sort(key=lambda item: item["source_key"])
    if len({row["source_key"] for row in review_rows}) != len(review_rows):
        raise PreparationError("review_key_collision")
    counts: dict = {"source_rows": len(sources), "requirement_labels": len(labels),
                    "review_candidates": len(review_rows), "loader_counts": batch.counts,
                    "exported": False}
    questions_data = None
    if approvals_path is not None:
        approvals = _load_approvals(Path(approvals_path))
        rows, export_counts = _build_approved_rows(review_rows, approvals)
        questions_data = _csv_bytes(CSV_COLUMNS, rows)
        counts.update(export_counts)
        counts["exported"] = True
    review_data = _csv_bytes(REVIEW_COLUMNS, review_rows)
    template_data = (_csv_bytes(APPROVAL_COLUMNS, [
        {"source_key": row["source_key"], "approved_question": ""} for row in review_rows
    ]) if approval_template is not None and approvals_path is None else None)
    report_data = (json.dumps(counts, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    # Do not partly replace prior outputs. Refuse non-identical existing files.
    for target, contents in ((review_output, review_data), (report_output, report_data),
                             (questions_output, questions_data),
                             (approval_template, template_data)):
        if contents is None:
            continue
        path = private_output_path(target, root)
        if path.exists() and (not path.is_file() or path.read_bytes() != contents):
            raise PreparationError("output_exists_different")
    _save_once(review_output, review_data, root)
    if template_data is not None:
        _save_once(approval_template, template_data, root)
    if questions_data is not None:
        _save_once(questions_output, questions_data, root)
    _save_once(report_output, report_data, root)
    return {"review_candidates": len(review_rows), "exported_rows": counts.get("exported_rows", 0),
            "exported": counts["exported"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True, help="Local source ZIP or TAR")
    parser.add_argument("--labels", type=Path, required=True, help="Local classification ZIP or TAR")
    parser.add_argument("--approvals", type=Path, help="Private manually reviewed CSV")
    parser.add_argument("--review-output", type=Path, default=PRIVATE_ROOT / "question_twin" / "review_candidates.csv")
    parser.add_argument("--approval-template", type=Path, default=PRIVATE_ROOT / "question_twin" / "approval_template.csv")
    parser.add_argument("--questions-output", type=Path, default=PRIVATE_ROOT / "question_twin" / "questions.csv")
    parser.add_argument("--report", type=Path, help="Private aggregate report destination")
    args = parser.parse_args(argv)
    report = args.report or PRIVATE_ROOT / "question_twin" / ("approved_report.json" if args.approvals else "review_report.json")
    try:
        result = prepare(sources_path=args.sources, labels_path=args.labels,
                         codes_path=CODES_PATH, review_output=args.review_output,
                         questions_output=args.questions_output, report_output=report,
                         approvals_path=args.approvals, approval_template=args.approval_template)
    except (DataError, PreparationError) as error:
        print(f"[error] {error}", file=sys.stderr)
        return 1
    except Exception:
        # Do not print tracebacks containing private filenames or provider text.
        print("[error] input_or_processing_failure (private details withheld)", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
