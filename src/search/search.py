from collections import Counter

FAKE_RESULTS = [
    {"id": 1, "question": "비밀번호를 잊어버렸어요", "score": 0.91, "category_code": "ACCOUNT"},
    {"id": 2, "question": "계정 암호를 재설정하고 싶어요", "score": 0.84, "category_code": "ACCOUNT"},
    {"id": 3, "question": "로그인이 되지 않습니다", "score": 0.72, "category_code": "LOGIN"},
    {"id": 4, "question": "아이디를 찾고 싶어요", "score": 0.61, "category_code": "ACCOUNT"},
    {"id": 5, "question": "회원 탈퇴는 어떻게 하나요", "score": 0.42, "category_code": "MEMBER"},
]


def search(query, top_k=5, threshold=0.7):
    # TODO(#7): 실제 임베딩 검색으로 교체
    return [
        {**item, "is_duplicate": item["score"] >= threshold}
        for item in FAKE_RESULTS[:top_k]
    ]


def suggest_codes(results):
    # TODO(#11): 동점 처리 규칙 추가
    counts = Counter(item["category_code"] for item in results)
    return [{"code": code, "count": count} for code, count in counts.most_common()]