"""TF-IDF 베이스라인 검색 (#9).

MiniLM 검색(src/search/search.py)과 비교하기 위한 기준 모델이다.
입출력은 docs/interface.md의 search()와 같다.

실행 (레포 최상위 폴더에서):
    python -m eval.tfidf_baseline "요금제 바꾸고 싶어요"
"""

import sys

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from eval.data_utils import load_questions


def make_vectorizer():
    # 한국어는 조사가 붙어 단어 단위가 잘 안 맞으므로 글자 2~4개 단위로 자른다.
    return TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))


class TfidfSearcher:
    def __init__(self, rows):
        self.rows = rows
        texts = []
        for row in rows:
            texts.append(row["question"])
        self.vectorizer = make_vectorizer()
        self.matrix = self.vectorizer.fit_transform(texts)

    def search(self, query, top_k=5, threshold=0.7):
        query = (query or "").strip()
        if not query or top_k <= 0:
            return []

        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix)[0]
        # 점수가 같으면 항상 같은 순서로 나오게 한다 (src/search/search.py와 같은 규칙)
        order = np.argsort(-scores, kind="stable")[:top_k]

        results = []
        for index in order:
            row = self.rows[index]
            score = float(scores[index])
            results.append({
                "id": row["id"],
                "question": row["question"],
                "score": round(score, 4),
                "category_code": row["category_code"],
                "is_duplicate": score >= threshold,
            })
        return results


def similarity_matrix(texts):
    """평가용: 질문끼리의 TF-IDF 코사인 유사도 행렬."""
    vectorizer = make_vectorizer()
    matrix = vectorizer.fit_transform(texts)
    return cosine_similarity(matrix)


_searcher = None


def search(query, top_k=5, threshold=0.7):
    """docs/interface.md의 search()와 같은 입출력 (샘플 질문에서 검색)."""
    global _searcher
    if _searcher is None:
        _searcher = TfidfSearcher(load_questions())
    return _searcher.search(query, top_k=top_k, threshold=threshold)


def main():
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "요금제 바꾸고 싶어요"

    print("질문:", query)
    rank = 1
    for item in search(query):
        print(f"{rank}. {item['score']:.4f} [{item['category_code']}] {item['question']}")
        rank += 1


if __name__ == "__main__":
    main()
