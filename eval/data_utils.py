"""평가용 데이터 읽기 도구.

질문 CSV 형식은 docs/interface.md를 따른다.
컬럼: id, question, category_code, duplicate_group, split
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "data" / "sample_questions.csv"
REQUIRED_COLUMNS = ["id", "question", "category_code", "duplicate_group"]


def load_questions(path=None):
    """CSV를 읽어 질문 목록(dict의 list)으로 돌려준다. 경로가 없으면 샘플 질문을 쓴다."""
    if path is None:
        path = SAMPLE_DATA

    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing = []
        for column in REQUIRED_COLUMNS:
            if column not in fieldnames:
                missing.append(column)
        if missing:
            raise ValueError(f"{path}에 필요한 컬럼이 없습니다: {missing}")

        for row in reader:
            rows.append({
                "id": int(row["id"]),
                "question": row["question"].strip(),
                "category_code": row["category_code"].strip(),
                "duplicate_group": row["duplicate_group"].strip(),
                "split": (row.get("split") or "").strip(),
            })
    return rows


def filter_split(rows, split):
    """split 값이 같은 질문만 고른다. split이 None이면 전체."""
    if split is None:
        return rows
    selected = []
    for row in rows:
        if row["split"] == split:
            selected.append(row)
    return selected
