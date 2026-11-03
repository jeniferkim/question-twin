"""CPU smoke test with synthetic Korean only; no paid API or private data input."""
import argparse
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import re
import sys
import time

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SENTENCES = ["휴대폰 요금제를 변경하고 싶어요.", "지금 쓰는 요금제를 바꿀 수 있나요?", "이번 달 요금 납부일이 언제인가요?"]


def run(args):
    started = time.perf_counter()
    result = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "model": MODEL, "revision": args.revision, "device": "cpu",
              "synthetic_inputs_only": True, "python": sys.version.split()[0],
              "download_allowed": args.download, "status": "failed", "packages": {}}
    try:
        for name in ("sentence-transformers", "transformers", "torch", "numpy", "huggingface-hub"):
            result["packages"][name] = metadata.version(name)
        import numpy as np
        import torch
        from sentence_transformers import SentenceTransformer

        torch.set_num_threads(2)
        model = SentenceTransformer(MODEL, revision=args.revision, device="cpu",
                                    cache_folder=str(args.cache),
                                    local_files_only=not args.download,
                                    trust_remote_code=False)
        limit = model.max_seq_length
        lengths = [len(model.tokenizer(s, truncation=False)["input_ids"]) for s in SENTENCES]
        result.update(max_seq_length=limit, input_char_lengths=list(map(len, SENTENCES)),
                      input_token_lengths=lengths,
                      inputs_exceeding_limit=sum(n > limit for n in lengths),
                      truncation="SentenceTransformer max_seq_length")
        vectors = model.encode(SENTENCES, convert_to_numpy=True,
                               normalize_embeddings=True, show_progress_bar=False)
        result.update(shape=list(vectors.shape), dtype=str(vectors.dtype),
                      finite=bool(np.isfinite(vectors).all()))
        if vectors.shape != (len(SENTENCES), 384) or not result["finite"]:
            result["error_code"] = "unexpected_embedding"
        else:
            result["status"] = "passed"
    except metadata.PackageNotFoundError:
        result["error_code"] = "missing_dependency"
    except Exception as error:
        # Avoid raw exception text (which may contain local paths or credentials).
        result["error_code"] = type(error).__name__
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True, help="Exact model commit SHA, 40 hexadecimal characters")
    parser.add_argument("--download", action="store_true", help="Explicitly allow public model download")
    parser.add_argument("--cache", type=Path, default=Path(__file__).resolve().parent / ".model_cache")
    parser.add_argument("--report", type=Path, default=Path(__file__).resolve().parent / "reports" / "minilm_smoke.json")
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-fA-F]{40}", args.revision) is None:
        parser.error("--revision must be an exact commit SHA")
    result = run(args)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
