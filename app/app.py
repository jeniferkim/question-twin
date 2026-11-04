import gradio as gr


def search(query: str, top_k: int = 5, threshold: float = 0.7) -> list[dict]:
    """가짜 search(): 모델이 연결되기 전까지 쓰는 임시 함수"""
    fake_results = [
        {"id": 101, "question": "예시 질문 1 (가짜 데이터)", "score": 0.95, "category_code": "A01"},
        {"id": 102, "question": "예시 질문 2 (가짜 데이터)", "score": 0.88, "category_code": "A01"},
        {"id": 103, "question": "예시 질문 3 (가짜 데이터)", "score": 0.76, "category_code": "B02"},
        {"id": 104, "question": "예시 질문 4 (가짜 데이터)", "score": 0.65, "category_code": "A01"},
        {"id": 105, "question": "예시 질문 5 (가짜 데이터)", "score": 0.52, "category_code": "C03"},
    ]
    for r in fake_results:
        r["is_duplicate"] = r["score"] >= threshold
    return fake_results[:top_k]


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