"""정답 데이터 검수 (#8).

실행 (레포 최상위 폴더에서):
    python -m eval.check_data
    python -m eval.check_data data/sample_questions.csv

문제가 있으면 [오류]/[주의]로 알려주고, 오류가 있으면 종료 코드 1을 돌려준다.
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "sample_questions.csv"
CODES_PATH = ROOT / "data" / "consult_codes.csv"
COLUMNS = ["id", "question", "category_code", "duplicate_group", "split"]
SPLITS = ("tune", "test")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = []
        for row in reader:
            clean = {}
            for key in fieldnames:
                clean[key] = (row.get(key) or "").strip()
            rows.append(clean)
    return fieldnames, rows


def check(rows, known_codes):
    """검수 결과를 (오류 목록, 주의 목록)으로 돌려준다."""
    errors = []
    warnings = []

    ids = Counter()
    texts = Counter()
    group_size = Counter()
    group_codes = defaultdict(set)
    group_splits = defaultdict(set)

    for row in rows:
        ids[row["id"]] += 1
        texts[row["question"]] += 1
        group = row["duplicate_group"]
        group_size[group] += 1
        group_codes[group].add(row["category_code"])
        group_splits[group].add(row["split"])

        if not row["id"].isdigit():
            errors.append(f"id는 숫자여야 함: {row['id']!r}")
        if row["question"] == "":
            errors.append(f"빈 질문: id {row['id']}")
        if group == "":
            errors.append(f"묶음 번호 없음: id {row['id']}")
        if row["split"] not in SPLITS:
            errors.append(f"split 값 오류: id {row['id']} -> {row['split']!r}")
        if known_codes and row["category_code"] not in known_codes:
            errors.append(f"목록에 없는 상담 코드: id {row['id']} -> {row['category_code']}")

    for value, count in ids.items():
        if count > 1:
            errors.append(f"id 중복: {value} ({count}번)")
    for value, count in texts.items():
        if count > 1:
            warnings.append(f"완전히 같은 질문 {count}개: {value}")

    for group in sorted(group_size):
        if len(group_codes[group]) > 1:
            errors.append(f"한 묶음에 상담 코드가 여러 개: {group} {sorted(group_codes[group])}")
        if len(group_splits[group]) > 1:
            errors.append(f"한 묶음이 tune과 test에 나뉨: {group}")
        if group_size[group] == 1:
            warnings.append(f"질문이 1개뿐인 묶음 (같은 의미 질문 찾기 평가에 못 씀): {group}")

    used_codes = set()
    for row in rows:
        used_codes.add(row["category_code"])
    for code in sorted(known_codes):
        if code not in used_codes:
            warnings.append(f"샘플에 한 번도 안 나온 상담 코드: {code}")

    return errors, warnings


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = DATA_PATH

    fieldnames, rows = read_csv(path)
    missing = []
    for column in COLUMNS:
        if column not in fieldnames:
            missing.append(column)
    if missing:
        print(f"[오류] {path}에 필요한 컬럼이 없습니다: {missing}")
        sys.exit(1)

    known_codes = set()
    if CODES_PATH.exists():
        for code_row in read_csv(CODES_PATH)[1]:
            known_codes.add(code_row["category_code"])

    errors, warnings = check(rows, known_codes)

    groups = set()
    split_questions = Counter()
    split_groups = defaultdict(set)
    for row in rows:
        groups.add(row["duplicate_group"])
        split_questions[row["split"]] += 1
        split_groups[row["split"]].add(row["duplicate_group"])

    try:
        shown = path.resolve().relative_to(ROOT)
    except ValueError:
        shown = path
    print(f"파일: {shown}")
    print(f"질문 수: {len(rows)}")
    print(f"질문 묶음 수: {len(groups)}")
    print(f"상담 코드 수: {len(known_codes)}")
    for split in SPLITS:
        print(f"{split}: 질문 {split_questions[split]}개 / 묶음 {len(split_groups[split])}개")
    print()
    for message in errors:
        print("[오류]", message)
    for message in warnings:
        print("[주의]", message)
    if not errors and not warnings:
        print("문제 없음")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
