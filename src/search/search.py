# 동작 방식
# 로컬에 실데이터 임베딩(data/embeddings/...)이 있으면 그걸로 검색하고,
# 없으면 샘플 질문 30개를 한 번만 숫자 벡터로 바꿔 메모리에 저장해서 검색
# 새 질문도 벡터로 바꿔서 유사도 높은 순서로 5개를 고름
# 유사도가 같으면 항상 같은 순서로 나옴
# QUESTION_TWIN_DATA=sample 이면 실데이터가 있어도 샘플로 검색


import csv
import os
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_questions.csv"
CODES_PATH = Path(__file__).resolve().parents[2] / "data" / "consult_codes.csv"
INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "embeddings" / "question_twin" / "minilm_index.npz"
MAX_QUERY_LENGTH = 500


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")


def _encode(texts):
    return _load_model().encode(texts, normalize_embeddings=True, convert_to_numpy=True)


@lru_cache(maxsize=1)
def _load_index():
    with open(DATA_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows, _encode([row["question"] for row in rows])


def _use_saved_index():
    return os.environ.get("QUESTION_TWIN_DATA") != "sample" and INDEX_PATH.exists()


@lru_cache(maxsize=1)
def _load_saved_index():
    from src.embedding.store import load_index

    return load_index(INDEX_PATH)


def data_source():
    """화면에 보여줄 검색 대상 설명"""
    if _use_saved_index():
        return f"실데이터 {len(_load_saved_index().ids)}건"
    with open(DATA_PATH, encoding="utf-8") as f:
        return f"샘플 {sum(1 for _ in csv.DictReader(f))}건"


def search(query, top_k=5, threshold=0.7):
    query = (query or "").strip()
    if not query or top_k <= 0:
        return []
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError("query_too_long")

    if _use_saved_index():
        return _load_saved_index().search(query, top_k=top_k, threshold=threshold, encoder=_load_model())

    rows, vectors = _load_index()
    scores = vectors @ _encode([query])[0]
    order = np.argsort(-scores, kind="stable")[:top_k]
    return [
        {
            "id": int(rows[i]["id"]),
            "question": rows[i]["question"],
            "score": round(float(scores[i]), 4),
            "category_code": rows[i]["category_code"],
            "is_duplicate": bool(scores[i] >= threshold),
        }
        for i in order
    ]


@lru_cache(maxsize=1)
def _code_names():
    with open(CODES_PATH, encoding="utf-8") as f:
        return {row["category_code"]: row["name"] for row in csv.DictReader(f)}


def suggest_codes(results):
    # 많이 나온 코드부터, 횟수가 같으면 검색 순위가 더 높은 코드부터 추천
    counts = Counter(item["category_code"] for item in results)
    first_rank = {}
    for rank, item in enumerate(results):
        first_rank.setdefault(item["category_code"], rank)

    names = _code_names()
    codes = sorted(counts, key=lambda code: (-counts[code], first_rank[code]))
    return [{"code": code, "name": names.get(code, code), "count": counts[code]} for code in codes]