"""Local-only MiniLM embedding archive, compatible with the existing search contract.

Run from the repository root: python -m src.embedding.store --help
Only save indices beneath gitignored data/embeddings/.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import zipfile

import numpy as np

from src.search.search import MODEL_NAME, MODEL_REVISION

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_ROOT = ROOT / "data" / "embeddings"
DEFAULT_SOURCE = ROOT / "data" / "raw" / "question_twin" / "questions.csv"
DEFAULT_INDEX = PRIVATE_ROOT / "question_twin" / "minilm_index.npz"
COLUMNS = {"id", "question", "category_code"}
DIM = 384
MAX_ROWS = 25000


class IndexErrorSafe(ValueError):
    """Stable validation errors excluding sensitive data and local paths."""


@dataclass(frozen=True)
class SavedIndex:
    ids: np.ndarray
    questions: np.ndarray
    category_codes: np.ndarray
    vectors: np.ndarray
    metadata: dict

    def search(self, query: str, *, top_k: int = 5, threshold: float = 0.7,
               encoder=None) -> list[dict]:
        if not isinstance(query, str) or not query.strip() or top_k <= 0:
            return []
        if encoder is None:
            encoder = load_model()
        query_vector = np.asarray(encoder.encode([query.strip()], normalize_embeddings=True,
                                                 convert_to_numpy=True), dtype=np.float32)
        if query_vector.shape != (1, DIM) or not np.isfinite(query_vector).all():
            raise IndexErrorSafe("invalid_query_embedding")
        if not np.isclose(np.linalg.norm(query_vector[0]), 1.0, atol=0.002):
            raise IndexErrorSafe("query_vector_not_normalized")
        scores = self.vectors @ query_vector[0]
        order = np.argsort(-scores, kind="stable")[:top_k]
        return [{"id": int(self.ids[i]), "question": str(self.questions[i]),
                 "score": round(float(scores[i]), 4),
                 "category_code": str(self.category_codes[i]),
                 "is_duplicate": bool(scores[i] >= threshold)} for i in order]


def _private_index_path(path: Path, root: Path = ROOT) -> Path:
    target = Path(path).resolve()
    allowed = (root / "data" / "embeddings").resolve()
    if target == allowed or not target.is_relative_to(allowed) or target.suffix.lower() != ".npz":
        raise IndexErrorSafe("index_must_be_under_data_embeddings")
    return target


def _csv_rows(csv_bytes: bytes) -> list[dict]:
    try:
        text = csv_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if not COLUMNS.issubset(reader.fieldnames or []):
            raise IndexErrorSafe("invalid_source_schema")
        rows = []
        seen = set()
        for item in reader:
            identifier = int(item["id"])
            question = item["question"]
            code = item["category_code"]
            if identifier <= 0 or identifier in seen or not question or not question.strip() or not code:
                raise IndexErrorSafe("invalid_source_row")
            if "\x00" in question or len(question) > 500:
                raise IndexErrorSafe("invalid_question_length")
            seen.add(identifier)
            rows.append({"id": identifier, "question": question, "category_code": code})
            if len(rows) > MAX_ROWS:
                raise IndexErrorSafe("row_limit")
    except IndexErrorSafe:
        raise
    except (ValueError, TypeError, KeyError, csv.Error, UnicodeError):
        raise IndexErrorSafe("invalid_source_csv") from None
    if not rows:
        raise IndexErrorSafe("empty_source_csv")
    rows.sort(key=lambda r: r["id"])
    return rows


def load_model(*, allow_download: bool = False):
    """The same MiniLM name/revision as src.search.search, CPU only."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu",
                               cache_folder=str(ROOT / "scripts" / ".model_cache"),
                               local_files_only=not allow_download, trust_remote_code=False)


def _validate_arrays(index: SavedIndex) -> None:
    n = len(index.ids)
    if (n == 0 or n > MAX_ROWS or index.vectors.shape != (n, DIM)
            or index.questions.shape != (n,) or index.category_codes.shape != (n,)
            or index.ids.shape != (n,)):
        raise IndexErrorSafe("invalid_index_shape")
    if len(set(map(int, index.ids))) != n or (index.ids <= 0).any():
        raise IndexErrorSafe("invalid_index_ids")
    if not np.isfinite(index.vectors).all():
        raise IndexErrorSafe("nonfinite_vectors")
    if not np.allclose(np.linalg.norm(index.vectors, axis=1), 1.0, atol=0.002):
        raise IndexErrorSafe("vectors_not_normalized")
    if any(not str(q).strip() or not str(code).strip() for q, code in zip(index.questions, index.category_codes)):
        raise IndexErrorSafe("invalid_index_rows")
    if not all(key in index.metadata for key in ("model", "revision", "source_sha256", "rows", "dimension")):
        raise IndexErrorSafe("invalid_index_metadata")
    if index.metadata["rows"] != n or index.metadata["dimension"] != DIM:
        raise IndexErrorSafe("index_metadata_mismatch")


def build_index(csv_path: Path, output_path: Path, *, encoder=None,
                allow_download: bool = False, root: Path = ROOT) -> dict:
    target = _private_index_path(output_path, root)
    if target.exists():
        raise IndexErrorSafe("index_exists_will_not_overwrite")
    source = Path(csv_path).read_bytes()
    rows = _csv_rows(source)
    if encoder is None:
        encoder = load_model(allow_download=allow_download)
    texts = [row["question"] for row in rows]
    started = time.perf_counter()
    vectors = np.asarray(encoder.encode(texts, batch_size=32, normalize_embeddings=True,
                                        convert_to_numpy=True, show_progress_bar=False), dtype=np.float32)
    elapsed = round(time.perf_counter() - started, 3)
    ids = np.asarray([row["id"] for row in rows], dtype=np.int64)
    questions = np.asarray(texts, dtype=np.str_)
    codes = np.asarray([row["category_code"] for row in rows], dtype=np.str_)
    metadata = {"model": MODEL_NAME, "revision": MODEL_REVISION,
                "source_sha256": hashlib.sha256(source).hexdigest(),
                "rows": len(rows), "dimension": DIM,
                "normalized": True, "device": "cpu"}
    index = SavedIndex(ids=ids, questions=questions, category_codes=codes,
                       vectors=vectors, metadata=metadata)
    _validate_arrays(index)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as file:
            np.savez_compressed(file, ids=ids, questions=questions, category_codes=codes,
                                vectors=vectors, metadata=np.array(json.dumps(metadata, sort_keys=True)))
    except FileExistsError:
        raise IndexErrorSafe("index_exists_will_not_overwrite") from None
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {"rows": len(rows), "dimension": DIM, "cpu_encode_seconds": elapsed,
            "model": MODEL_NAME, "revision": MODEL_REVISION}


def load_index(index_path: Path, *, csv_path: Path | None = None) -> SavedIndex:
    try:
        with np.load(index_path, allow_pickle=False) as file:
            if set(file.files) != {"ids", "questions", "category_codes", "vectors", "metadata"}:
                raise IndexErrorSafe("invalid_index_fields")
            metadata = json.loads(str(file["metadata"].item()))
            saved = SavedIndex(ids=file["ids"], questions=file["questions"],
                               category_codes=file["category_codes"], vectors=file["vectors"],
                               metadata=metadata)
    except IndexErrorSafe:
        raise
    except (OSError, ValueError, KeyError, TypeError, EOFError, zipfile.BadZipFile):
        raise IndexErrorSafe("cannot_read_index") from None
    _validate_arrays(saved)
    if saved.metadata["model"] != MODEL_NAME or saved.metadata["revision"] != MODEL_REVISION:
        raise IndexErrorSafe("model_version_mismatch")
    if csv_path is not None:
        raw = Path(csv_path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != saved.metadata["source_sha256"]:
            raise IndexErrorSafe("source_csv_changed")
        rows = _csv_rows(raw)
        if len(rows) != len(saved.ids):
            raise IndexErrorSafe("source_csv_changed")
        for i, row in enumerate(rows):
            if (row["id"] != int(saved.ids[i]) or row["question"] != saved.questions[i]
                    or row["category_code"] != saved.category_codes[i]):
                raise IndexErrorSafe("source_csv_changed")
    return saved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Create a private, versioned MiniLM index")
    build.add_argument("--csv", type=Path, default=DEFAULT_SOURCE)
    build.add_argument("--output", type=Path, default=DEFAULT_INDEX)
    build.add_argument("--allow-download", action="store_true", help="Explicitly allow public model download")
    verify = sub.add_parser("verify", help="Validate saved index and optional source CSV")
    verify.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    verify.add_argument("--csv", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = build_index(args.csv, args.output, allow_download=args.allow_download)
        else:
            _private_index_path(args.index)
            loaded = load_index(args.index, csv_path=args.csv)
            result = {"status": "passed", "rows": len(loaded.ids), "dimension": loaded.vectors.shape[1],
                      "model": loaded.metadata["model"], "revision": loaded.metadata["revision"]}
    except IndexErrorSafe as error:
        print(f"[error] {error}", file=sys.stderr)
        return 1
    except Exception:
        # Avoid tracebacks with local private paths or model cache metadata.
        print("[error] model_or_processing_failure (private details withheld)", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
