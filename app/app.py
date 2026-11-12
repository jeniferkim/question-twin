import gradio as gr

from src.search.search import search


def on_search(query, threshold):
    if not query or not query.strip():
        gr.Warning("질문을 입력해 주세요.")
        return []

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
    return rows


with gr.Blocks(title="중복 질문 찾기") as demo:
    gr.Markdown("# 표현이 다른 중복 질문 찾기")
    query_box = gr.Textbox(label="질문 입력", placeholder="질문을 입력하세요")
    threshold_slider = gr.Slider(
        minimum=0.0,
        maximum=1.0,
        value=0.7,
        step=0.05,
        label="중복 기준값 (유사도가 이 값 이상이면 중복 후보)",
    )
    search_btn = gr.Button("검색")
    result_table = gr.Dataframe(
        headers=["순위", "ID", "유사 질문", "유사도", "상담 코드", "중복 여부"],
        interactive=False,
    )
    search_btn.click(
        fn=on_search,
        inputs=[query_box, threshold_slider],
        outputs=result_table,
    )
    query_box.submit(
        fn=on_search,
        inputs=[query_box, threshold_slider],
        outputs=result_table,
    )

if __name__ == "__main__":
    demo.launch()