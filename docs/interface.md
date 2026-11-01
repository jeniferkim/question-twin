# 입출력 규칙

## 데이터 형식

파일: `data/questions.csv`

| 컬럼              | 설명                       |
| ----------------- | -------------------------- |
| `id`              | 질문 고유 번호             |
| `question`        | 질문 내용                  |
| `category_code`   | 상담 코드                  |
| `duplicate_group` | 같은 의미의 질문 묶음 번호 |
| `split`           | `tune` 또는 `test`         |

## search

```python
search(query: str, top_k: int = 5, threshold: float = 0.7) -> list[dict]
```

결과 항목:

| 키              | 설명                      |
| --------------- | ------------------------- |
| `id`            | 질문 고유 번호            |
| `question`      | 유사 질문                 |
| `score`         | 유사도 점수               |
| `category_code` | 상담 코드                 |
| `is_duplicate`  | `score >= threshold` 여부 |

## suggest_codes

```python
suggest_codes(results: list[dict]) -> list[dict]
```

결과 항목:

| 키      | 설명                  |
| ------- | --------------------- |
| `code`  | 상담 코드             |
| `count` | 검색 결과에 나온 횟수 |

`threshold`의 `0.7`은 임시값이며, 평가 후 변경합니다.
