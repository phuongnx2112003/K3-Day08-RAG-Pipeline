"""Streamlit chatbot cho Book Insights Hybrid RAG.

Chạy trên Windows:
    .\.venv\Scripts\python.exe -m streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.supervisor import PipelineSupervisor
from src.task10_generation import LLM_MODEL, generate_with_citation


st.set_page_config(
    page_title="Book Insights RAG Chatbot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"📚 Nguồn tham khảo ({len(sources)} chunks)"):
        for index, source in enumerate(sources, start=1):
            metadata = source.get("metadata") or {}
            citation_id = metadata.get("citation_id", f"S{index}")
            title = metadata.get("title") or metadata.get("display_source") or metadata.get("source", "Unknown")
            author = metadata.get("author", "")
            source_url = metadata.get("source_url", "")
            retrieval = source.get("source", metadata.get("retrieval_mode", "hybrid"))
            score = float(source.get("score", 0.0))

            heading = f"**[{citation_id}] {title}**"
            if source_url:
                heading = f"**[{citation_id}] [{title}]({source_url})**"
            st.markdown(heading)
            details = [f"retrieval: `{retrieval}`", f"score: `{score:.4f}`"]
            if author:
                details.insert(0, f"tác giả: `{author}`")
            st.caption(" · ".join(details))
            preview = source.get("content", "").strip()
            st.text(preview[:500] + ("..." if len(preview) > 500 else ""))
            if index < len(sources):
                st.divider()


if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


with st.sidebar:
    st.title("📚 Book Insights RAG")
    st.caption("Tóm tắt và phân tích sách dựa trên evidence có citation")

    st.subheader("💡 Câu hỏi gợi ý")
    suggestions = [
        "Phương pháp 4 bước xây dựng thói quen theo Atomic Habits là gì?",
        "Hệ thống 1 và Hệ thống 2 khác nhau như thế nào?",
        "Validated learning trong The Lean Startup là gì?",
        "Atomic Habits khuyên tập trung vào hệ thống thay vì mục tiêu ra sao?",
        "Giá Bitcoin hôm nay là bao nhiêu?",
    ]
    for suggestion in suggestions:
        if st.button(suggestion, use_container_width=True, key=f"suggestion-{suggestion}"):
            st.session_state.pending_query = suggestion

    st.divider()
    st.subheader("⚙️ Thiết lập")
    top_k = st.slider("Số chunks", min_value=3, max_value=10, value=5)
    score_threshold = st.slider(
        "Ngưỡng fallback cosine",
        min_value=0.20,
        max_value=0.60,
        value=0.40,
        step=0.05,
        help="Dùng cosine gốc của dense retrieval; không dùng RRF score.",
    )
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_query = None
        st.rerun()

    st.divider()
    st.caption(f"Model generation: `{LLM_MODEL}`")
    st.caption("Dense + BM25 → RRF → PageIndex fallback → OpenAI + citations")
    health = PipelineSupervisor().health_check()
    if all(item.ready for item in health):
        st.success("Task 9/10 READY")
    else:
        for item in health:
            if not item.ready:
                st.error(f"{item.component}: {item.detail}")


st.title("📚 Trợ Lý Review & Tóm Tắt Sách")
st.caption("Câu trả lời chỉ dựa trên corpus đã index; thiếu evidence sẽ từ chối xác minh.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            retrieval_source = message.get("retrieval_source", "none")
            model = message.get("model")
            caption = f"retrieval: `{retrieval_source}`"
            if model:
                caption += f" · model: `{model}`"
            st.caption(caption)
            render_sources(message.get("sources", []))


typed_query = st.chat_input("Nhập câu hỏi về nội dung hoặc bài học từ sách...")
query = typed_query or st.session_state.pending_query

if query:
    st.session_state.pending_query = None
    history = list(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm evidence và tạo câu trả lời có citation..."):
            try:
                response = generate_with_citation(
                    query,
                    top_k=top_k,
                    conversation=history,
                    score_threshold=score_threshold,
                )
                answer = response["answer"]
                sources = response.get("sources", [])
                retrieval_source = response.get("retrieval_source", "none")
                model = response.get("model")
                citations_valid = response.get("citations_valid", True)
            except Exception as exc:
                answer = f"❌ Không thể hoàn tất RAG pipeline: `{type(exc).__name__}: {exc}`"
                sources = []
                retrieval_source = "error"
                model = None
                citations_valid = False

            st.markdown(answer)
            st.caption(
                f"retrieval: `{retrieval_source}`"
                + (f" · model: `{model}`" if model else "")
            )
            if not citations_valid:
                st.warning("Citation do model trả về chưa vượt qua kiểm tra ID nguồn.")
            render_sources(sources)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_source": retrieval_source,
            "model": model,
            "citations_valid": citations_valid,
        }
    )
