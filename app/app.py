import gradio as gr

from src.search.search import MAX_QUERY_LENGTH, search, suggest_codes

SAMPLE_QUESTIONS = [
    ["요금제 좀 다른 걸로 바꿀 수 있을까요?"],
    ["핸드폰 분실했는데 정지해 주세요"],
    ["소액결제 못 하게 막아 주세요"],
    ["이번 달 요금이 너무 많이 나왔어요"],
]


def on_search(query, threshold):
    if not query or not query.strip():
        gr.Warning("질문을 입력해 주세요.")
        return [], []
    if len(query.strip()) > MAX_QUERY_LENGTH:
        gr.Warning(f"질문은 {MAX_QUERY_LENGTH}자 이하로 입력해 주세요.")
        return [], []

    results = search(query, top_k=5, threshold=threshold)
    rows = []
    for rank, r in enumerate(results, start=1):
        rows.append([
            rank,
            r["id"],
            r["question"],
            r["score"],
            r["category_code"],
            "예" if r["is_duplicate"] else "아니오",
        ])

    code_rows = []
    for rank, c in enumerate(suggest_codes(results), start=1):
        code_rows.append([rank, c["code"], c["name"], c["count"]])

    return rows, code_rows


with gr.Blocks(title="중복 질문 찾기") as demo:
    gr.Markdown("# 표현이 다른 중복 질문 찾기")
    query_box = gr.Textbox(label="질문 입력", placeholder="질문을 입력하세요")
    gr.Examples(
        examples=SAMPLE_QUESTIONS,
        inputs=query_box,
        label="샘플 질문 (누르면 입력창에 들어갑니다)",
    )
    threshold_slider = gr.Slider(
        minimum=0.0,
        maximum=1.0,
        value=0.7,
        step=0.05,
        label="중복 기준값 (유사도가 이 값 이상이면 중복 후보)",
    )
    search_btn = gr.Button("검색")

    gr.Markdown("### 유사 질문")
    result_table = gr.Dataframe(
        headers=["순위", "ID", "유사 질문", "유사도", "상담 코드", "중복 여부"],
        interactive=False,
    )

    gr.Markdown(
        "### 상담 코드 후보\n"
        "아래 코드는 검색 결과를 바탕으로 자동 추천한 **사용자 검토용 후보**입니다. "
        "최종 상담 코드는 직접 확인한 뒤 정해 주세요."
    )
    code_table = gr.Dataframe(
        headers=["순위", "상담 코드", "코드 이름", "나온 횟수"],
        interactive=False,
    )

    search_btn.click(
        fn=on_search,
        inputs=[query_box, threshold_slider],
        outputs=[result_table, code_table],
    )
    query_box.submit(
        fn=on_search,
        inputs=[query_box, threshold_slider],
        outputs=[result_table, code_table],
    )

if __name__ == "__main__":
    demo.launch()