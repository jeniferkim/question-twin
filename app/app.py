import gradio as gr

from src.search.search import search


def on_search(query):
    results = search(query)
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
    search_btn = gr.Button("검색")
    result_table = gr.Dataframe(
        headers=["순위", "ID", "유사 질문", "유사도", "상담 코드", "중복 여부"],
        interactive=False,
    )
    search_btn.click(fn=on_search, inputs=query_box, outputs=result_table)

if __name__ == "__main__":
    demo.launch()