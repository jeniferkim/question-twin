"""Issue #2 feasibility draft. No disk extraction, CSV export, or search integration.

Synthetic tests and local provider schema/join checks have been run.
Request semantics still require manual review. Candidate text is private.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from io import BytesIO
import json
import re
import stat
import tarfile
from typing import BinaryIO, Iterable, Mapping
import zipfile


class DataError(ValueError):
    """Stable error codes only: do not include member names, IDs, or raw text."""


@dataclass(frozen=True)
class Limits:
    member_bytes: int = 16 * 1024 * 1024
    zip_bytes: int = 128 * 1024 * 1024
    total_bytes: int = 512 * 1024 * 1024
    members: int = 25000
    ratio: int = 200
    records: int = 25000

    def __post_init__(self):
        if any(value <= 0 for value in vars(self).values()):
            raise ValueError("invalid_limits")


@dataclass
class _Budget:
    limits: Limits
    bytes: int = 0
    members: int = 0
    records: int = 0

    def member(self):
        self.members += 1
        if self.members > self.limits.members:
            raise DataError("member_limit")

    def read(self, stream: BinaryIO, expected: int, maximum: int) -> bytes:
        if expected < 0 or expected > maximum:
            raise DataError("size_limit")
        remaining = self.limits.total_bytes - self.bytes
        if expected > remaining:
            raise DataError("total_size_limit")
        value = stream.read(min(expected, remaining, maximum) + 1)
        self.bytes += len(value)
        if len(value) != expected:
            raise DataError("size_mismatch")
        return value


def _suffix(name: str) -> str:
    # A leading slash occurs in provider ZIPs. Names are opaque, never paths.
    name = name.replace("\\", "/")
    if "\x00" in name or ".." in name.split("/"):
        raise DataError("unsafe_member_name")
    return name.rsplit(".", 1)[-1].lower()


def _parse_json(raw: bytes, budget: _Budget) -> list[dict]:
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DataError("duplicate_json_key")
            result[key] = value
        return result

    def reject_constant(_):
        raise DataError("invalid_json_constant")

    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_keys,
                           parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise DataError("invalid_json") from None
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise DataError("expected_record_list")
    budget.records += len(value)
    if budget.records > budget.limits.records:
        raise DataError("record_limit")
    return value


def _read_zip(stream: BinaryIO, budget: _Budget) -> list[dict]:
    rows = []
    with zipfile.ZipFile(stream) as archive:
        for info in archive.infolist():
            budget.member()
            suffix = _suffix(info.filename)
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode) or info.flag_bits & 1:
                raise DataError("unsupported_zip_member")
            if info.is_dir():
                continue
            if suffix != "json":
                raise DataError("unsupported_member_type")
            if info.file_size > max(info.compress_size, 1) * budget.limits.ratio:
                raise DataError("compression_ratio_limit")
            with archive.open(info) as member:
                raw = budget.read(member, info.file_size, budget.limits.member_bytes)
            rows.extend(_parse_json(raw, budget))
    return rows


def read_archive(stream: BinaryIO, kind: str, limits: Limits = Limits()) -> list[dict]:
    """Read ZIP or uncompressed TAR->ZIP/JSON in memory; fail without partial output.

    Total budget counts ZIP container bytes AND JSON bytes. Compressed TAR is
    deliberately unsupported until an outer decompression budget is implemented.
    No archive member is ever extracted to a filesystem location.
    """
    if kind not in {"zip", "tar"}:
        raise DataError("unsupported_archive_type")
    budget = _Budget(limits)
    try:
        if kind == "zip":
            return _read_zip(stream, budget)
        rows = []
        with tarfile.open(fileobj=stream, mode="r|") as archive:
            for info in archive:
                budget.member()
                suffix = _suffix(info.name)
                # AI Hub TAR downloads may contain a complete ZIP named .zip.part0.
                # Never concatenate parts implicitly; ZipFile validates completeness.
                if re.search(r"\.zip\.part0$", info.name, flags=re.IGNORECASE):
                    suffix = "zip"
                if info.isdir():
                    continue
                if not info.isfile() or getattr(info, "sparse", None):
                    raise DataError("unsupported_tar_member")
                if suffix not in {"zip", "json"}:
                    raise DataError("unsupported_member_type")
                maximum = limits.zip_bytes if suffix == "zip" else limits.member_bytes
                member = archive.extractfile(info)
                if member is None:
                    raise DataError("unreadable_member")
                with member:
                    raw = budget.read(member, info.size, maximum)
                rows.extend(_read_zip(BytesIO(raw), budget) if suffix == "zip"
                            else _parse_json(raw, budget))
        return rows
    except DataError:
        raise
    except (OSError, EOFError, RuntimeError, ValueError, NotImplementedError,
            tarfile.TarError, zipfile.BadZipFile, RecursionError):
        raise DataError("invalid_archive") from None


@dataclass(frozen=True)
class SourceRecord:
    source_id: str = field(repr=False)
    category: str = field(repr=False)
    transcript: str = field(repr=False)


@dataclass(frozen=True)
class RequirementLabel:
    source_id: str = field(repr=False)
    category: str = field(repr=False)
    requirement: str = field(repr=False)


@dataclass(frozen=True)
class Candidate:
    source_id: str = field(repr=False)
    question: str = field(repr=False)
    category_code: str
    status: str = "needs_manual_review"


@dataclass(frozen=True)
class Selection:
    text: str | None = field(repr=False)
    reason: str


@dataclass(frozen=True)
class ExtractionConfig:
    domain_pattern: str = r"요금|납부|부가서비스|소액.?결제|선택약정|분실|정지|파손"
    request_pattern: str = r"싶|주세요|주실|문의|궁금|어떻게|얼마|언제|왜|되나요|나요|안.?돼|안.?되|없어요"
    multiple_pattern: str = r"그리고|또한|동시에|추가로|도\s*(?:문의|궁금)|[?？].+"
    trivial_pattern: str = r"(?:네|예|아니요|감사합니다|고맙습니다|여보세요|안녕하세요|잠시만요)[.!?\s]*"
    min_chars: int = 6
    max_chars: int = 500


def first_request(transcript: str, config: ExtractionConfig = ExtractionConfig()) -> Selection:
    """Conservative, unvalidated heuristic; ambiguous early turns block later ones."""
    if not isinstance(transcript, str) or not transcript.strip():
        return Selection(None, "invalid_transcript")
    turns = []
    for line in transcript.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.fullmatch(r"(고객|상담사)\s*[:：]\s*(.*)", line)
        if match is None:
            return Selection(None, "unrecognized_turn_format")
        if match[1] == "고객":
            turns.append(match[2].strip())
    for text in turns:
        if not text or re.fullmatch(config.trivial_pattern, text):
            continue
        # Do not remove de-identification tags or claim that a regex proves privacy.
        if re.search(r"<[^>]*>|\d{3}[- ]?\d{3,4}[- ]?\d{4}|[\w.+-]+@[\w.-]+", text):
            return Selection(None, "privacy_or_tag_review")
        if not config.min_chars <= len(text) <= config.max_chars:
            return Selection(None, "length_review")
        if re.search(config.multiple_pattern, text):
            return Selection(None, "multiple_request_review")
        if re.search(config.domain_pattern, text) and re.search(config.request_pattern, text):
            return Selection(text, "candidate")
        return Selection(None, "ambiguous_first_turn")
    return Selection(None, "no_customer_request")


@dataclass
class CandidateBatch:
    candidates: list[Candidate] = field(repr=False)
    counts: dict[str, int]


def extract_candidates(sources: Iterable[SourceRecord], labels: Iterable[RequirementLabel],
                       category_map: Mapping[str, str], *,
                       single_requirement: str = "단일 요건 민원",
                       config: ExtractionConfig = ExtractionConfig()) -> CandidateBatch:
    """Join normalized internal IDs, never filenames. Labels must be preselected.

    category_map uses exact source strings. No whitespace-based category merging.
    Duplicate IDs are quarantined even when their content is identical.
    Each unique source ID has exactly one outcome. Row anomalies are separate.
    """
    source_index, label_index = defaultdict(list), defaultdict(list)
    counts = Counter()
    for item in sources:
        counts["source_rows"] += 1
        if not isinstance(item, SourceRecord) or not isinstance(item.source_id, str) or not item.source_id:
            counts["invalid_source_rows"] += 1
            continue
        source_index[item.source_id].append(item)
    for item in labels:
        counts["label_rows"] += 1
        if not isinstance(item, RequirementLabel) or not isinstance(item.source_id, str) or not item.source_id:
            counts["invalid_label_rows"] += 1
            continue
        label_index[item.source_id].append(item)
    counts["orphan_label_ids"] = len(label_index.keys() - source_index.keys())
    counts["duplicate_label_ids"] = sum(len(v) > 1 for v in label_index.values())
    candidates = []
    for source_id in sorted(source_index):
        source_items = source_index[source_id]
        matches = label_index.get(source_id, [])
        if len(source_items) != 1:
            counts["duplicate_source_ids"] += 1
            continue
        if not matches:
            counts["missing_label"] += 1
            continue
        if len(matches) != 1:
            counts["conflicting_label"] += 1
            continue
        source, label = source_items[0], matches[0]
        if source.category != label.category:
            counts["category_mismatch"] += 1
            continue
        if label.requirement != single_requirement:
            counts["non_single_requirement"] += 1
            continue
        if source.category not in category_map:
            counts["unmapped_category"] += 1
            continue
        selection = first_request(source.transcript, config)
        counts[selection.reason] += 1
        if selection.text is not None:
            candidates.append(Candidate(source_id, selection.text, category_map[source.category]))
    counts["unique_source_ids"] = len(source_index)
    return CandidateBatch(candidates, dict(sorted(counts.items())))
