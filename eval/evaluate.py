"""MiniLM과 TF-IDF 검색 성능 비교 (#13).

실행 (레포 최상위 폴더에서):
    python -m eval.evaluate
    python -m eval.evaluate --real 실데이터.csv

1) 샘플 30개 (data/sample_questions.csv)
   - 질문 하나씩 넣고 나머지 29개에서 검색한다.
   - Top 1 정확도: 1등이 같은 묶음(duplicate_group)인 비율
   - Top 5 포함률: 5개 안에 같은 묶음이 하나라도 있는 비율
   - 결과는 eval/results/sample_metrics.md에도 저장한다. (직접 만든 문장이라 올려도 됨)
   - 1등이 틀린 사례와 유형은 eval/results/sample_errors.md에 저장한다.

2) 실데이터 (data/raw/question_twin/questions.csv가 있을 때만)
   - 질문 하나씩 넣고 나머지에서 Top 5를 검색한다.
   - 같은 상담 코드 비율: 5개 중 같은 상담 코드 개수 / 5 의 평균
   - 숫자만 화면에 출력하고 파일로 저장하지 않는다. (실데이터는 Git에 올리지 않음)

무작위: 검색 없이 무작위로 골랐을 때의 기댓값 (비교 기준).
"""

import argparse
from collections import Counter
from math import comb
from pathlib import Path

import numpy as np

from eval.data_utils import SAMPLE_DATA, load_questions
from eval.tfidf_baseline import similarity_matrix

ROOT = Path(__file__).resolve().parents[1]
REAL_DATA = ROOT / "data" / "raw" / "question_twin" / "questions.csv"
SAMPLE_RESULT = ROOT / "eval" / "results" / "sample_metrics.md"
SAMPLE_ERRORS = ROOT / "eval" / "results" / "sample_errors.md"
TOP_K = 5
SAME_CODE = "같은 상담 코드, 다른 요청"
OTHER_CODE = "다른 상담 코드"


def minilm_similarity(texts):
    # 앱과 같은 모델·revision을 쓰도록 src/search/search.py의 함수를 그대로 쓴다.
    from src.search.search import _encode

    vectors = np.asarray(_encode(texts), dtype=np.float64)
    return vectors @ vectors.T


def tfidf_similarity(texts):
    return similarity_matrix(texts)


METHODS = [
    ("MiniLM", minilm_similarity),
    ("TF-IDF", tfidf_similarity),
]


def top_neighbors(similarity, k):
    """질문마다 자기 자신을 뺀 유사도 상위 k개의 번호 (점수가 같으면 앞 번호 먼저)."""
    count = similarity.shape[0]
    result = []
    for i in range(count):
        scores = np.array(similarity[i], dtype=np.float64)
        order = np.argsort(-scores, kind="stable")
        top = []
        for j in order:
            if j == i:
                continue
            top.append(int(j))
            if len(top) == k:
                break
        result.append(top)
    return result


def group_hits(neighbors, groups):
    """(Top 1 맞힌 수, Top k 안에 있는 수)"""
    top1 = 0
    topk = 0
    for i, top in enumerate(neighbors):
        found = False
        for rank, j in enumerate(top):
            if groups[j] == groups[i]:
                if rank == 0:
                    top1 += 1
                found = True
        if found:
            topk += 1
    return top1, topk


def same_label_ratios(neighbors, labels):
    """질문마다 Top k 중 같은 라벨 비율"""
    ratios = []
    for i, top in enumerate(neighbors):
        same = 0
        for j in top:
            if labels[j] == labels[i]:
                same += 1
        ratios.append(same / len(top))
    return ratios


def top1_errors(neighbors, rows):
    """1등이 같은 묶음이 아닌 질문들: (질문 번호, 1등 번호, 유형) 목록"""
    errors = []
    for i, top in enumerate(neighbors):
        first = top[0]
        if rows[first]["duplicate_group"] == rows[i]["duplicate_group"]:
            continue
        if rows[first]["category_code"] == rows[i]["category_code"]:
            kind = SAME_CODE
        else:
            kind = OTHER_CODE
        errors.append((i, first, kind))
    return errors


def error_report(name, errors, rows):
    kinds = Counter()
    for _, _, kind in errors:
        kinds[kind] += 1

    summary = []
    summary.append(f"### {name}: 1등이 틀린 질문 {len(errors)}개")
    summary.append("")
    summary.append("| 유형 | 개수 |")
    summary.append("| --- | ---: |")
    summary.append(f"| {SAME_CODE} | {kinds[SAME_CODE]} |")
    summary.append(f"| {OTHER_CODE} | {kinds[OTHER_CODE]} |")

    cases = []
    cases.append("")
    cases.append("| 질문 | 1등으로 나온 질문 | 유형 |")
    cases.append("| --- | --- | --- |")
    for i, first, kind in errors:
        query = rows[i]
        found = rows[first]
        cases.append(f"| {query['question']} ({query['duplicate_group']}, {query['category_code']}) "
                     f"| {found['question']} ({found['duplicate_group']}, {found['category_code']}) "
                     f"| {kind} |")
    return summary, cases


def random_group_rates(groups, k):
    """무작위로 k개를 골랐을 때 (Top 1 정확도, Top k 포함률)의 기댓값"""
    count = len(groups)
    sizes = Counter(groups)
    top1 = 0.0
    topk = 0.0
    for group in groups:
        others = count - 1
        same = sizes[group] - 1
        picked = min(k, others)
        top1 += same / others
        topk += 1 - comb(others - same, picked) / comb(others, picked)
    return top1 / count, topk / count


def random_label_ratio(labels):
    """무작위로 골랐을 때 같은 라벨 비율의 기댓값"""
    count = len(labels)
    sizes = Counter(labels)
    total = 0.0
    for label in labels:
        total += (sizes[label] - 1) / (count - 1)
    return total / count


def percent(value):
    return f"{value * 100:.1f}%"


def evaluate_sample(path):
    rows = load_questions(path)
    texts = []
    groups = []
    for row in rows:
        texts.append(row["question"])
        groups.append(row["duplicate_group"])
    count = len(rows)

    lines = []
    lines.append(f"## 샘플 {count}개 (같은 의미 묶음 기준)")
    lines.append("")
    lines.append("질문 하나씩 넣고 나머지에서 검색했을 때")
    lines.append("")
    lines.append("| 방법 | Top 1 정확도 | Top 5 포함률 |")
    lines.append("| --- | ---: | ---: |")
    summaries = []
    details = []
    for name, similarity in METHODS:
        neighbors = top_neighbors(similarity(texts), TOP_K)
        top1, topk = group_hits(neighbors, groups)
        lines.append(f"| {name} | {percent(top1 / count)} ({top1}/{count}) "
                     f"| {percent(topk / count)} ({topk}/{count}) |")
        summary, cases = error_report(name, top1_errors(neighbors, rows), rows)
        summaries.extend(summary)
        summaries.append("")
        details.extend(summary)
        details.extend(cases)
        details.append("")
    random_top1, random_topk = random_group_rates(groups, TOP_K)
    lines.append(f"| 무작위 | {percent(random_top1)} | {percent(random_topk)} |")
    return lines, summaries, details


def evaluate_real(path):
    rows = load_questions(path)
    texts = []
    codes = []
    for row in rows:
        texts.append(row["question"])
        codes.append(row["category_code"])
    count = len(rows)
    if count < 2:
        return [f"실데이터 질문이 {count}개라 평가할 수 없습니다."]

    code_counts = Counter(codes)
    per_method = []
    for name, similarity in METHODS:
        neighbors = top_neighbors(similarity(texts), TOP_K)
        per_method.append((name, same_label_ratios(neighbors, codes)))

    lines = []
    lines.append(f"## 실데이터 {count}건 (같은 상담 코드 비율)")
    lines.append("")
    lines.append("질문 하나씩 넣고 나머지에서 Top 5를 검색했을 때, 5개 중 같은 상담 코드의 비율 평균")
    lines.append("")
    lines.append("| 방법 | 같은 상담 코드 비율 |")
    lines.append("| --- | ---: |")
    for name, ratios in per_method:
        lines.append(f"| {name} | {percent(sum(ratios) / count)} |")
    lines.append(f"| 무작위 | {percent(random_label_ratio(codes))} |")

    lines.append("")
    lines.append("### 상담 코드별")
    lines.append("")
    header = "| 상담 코드 | 질문 수 |"
    divider = "| --- | ---: |"
    for name, _ in per_method:
        header += f" {name} |"
        divider += " ---: |"
    lines.append(header)
    lines.append(divider)
    for code in sorted(code_counts, key=lambda c: (-code_counts[c], c)):
        line = f"| {code} | {code_counts[code]} |"
        for _, ratios in per_method:
            total = 0.0
            for i in range(count):
                if codes[i] == code:
                    total += ratios[i]
            line += f" {percent(total / code_counts[code])} |"
        lines.append(line)
    return lines


def main():
    parser = argparse.ArgumentParser(description="MiniLM과 TF-IDF 검색 성능 비교 (#13)")
    parser.add_argument("--sample", default=str(SAMPLE_DATA), help="샘플 질문 CSV")
    parser.add_argument("--real", default=str(REAL_DATA), help="실데이터 질문 CSV (없으면 건너뜀)")
    args = parser.parse_args()

    sample_lines, error_summaries, error_details = evaluate_sample(args.sample)
    SAMPLE_RESULT.parent.mkdir(parents=True, exist_ok=True)
    with open(SAMPLE_RESULT, "w", encoding="utf-8") as f:
        f.write("# 샘플 평가 결과\n\n")
        f.write("`python -m eval.evaluate`로 생성\n\n")
        f.write("\n".join(sample_lines) + "\n")
    with open(SAMPLE_ERRORS, "w", encoding="utf-8") as f:
        f.write("# 샘플 오류 사례\n\n")
        f.write("`python -m eval.evaluate`로 생성. 질문 하나씩 넣었을 때 1등으로 나온 질문이 같은 묶음이 아닌 경우\n\n")
        f.write("- 같은 상담 코드, 다른 요청: 주제는 같지만 필요한 답이 다른 질문을 1등으로 고름\n")
        f.write("- 다른 상담 코드: 표현만 겹치는 다른 주제의 질문을 1등으로 고름\n\n")
        f.write("\n".join(error_details) + "\n")
    print("\n".join(sample_lines))
    print()
    print("\n".join(error_summaries))
    print(f"(저장: {SAMPLE_RESULT.relative_to(ROOT)}, {SAMPLE_ERRORS.relative_to(ROOT)})")
    print()

    real_path = Path(args.real)
    if real_path.exists():
        print("\n".join(evaluate_real(real_path)))
        print()
        print("(실데이터 결과는 파일로 저장하지 않습니다. 숫자만 복사해서 공유해 주세요.)")
    else:
        print("실데이터 파일이 없어 실데이터 평가는 건너뜁니다.")


if __name__ == "__main__":
    main()
