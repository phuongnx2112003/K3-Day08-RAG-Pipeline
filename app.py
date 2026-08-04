"""
RAG Chatbot — Book Review & Summary Assistant.
Streamlit app kết nối RAG Retrieval (Task 9) và Generation (Task 10).

Chạy:
    streamlit run app.py
"""

import os
import sys
import html
import re
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Thêm project root vào sys.path để import các task từ src/
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def render_answer_with_citation_tooltips(answer: str, sources: list[dict], anchor_prefix: str) -> str:
    """Render model citations as hoverable source excerpts without trusting model HTML."""
    def legacy_citation_to_chunks(match: re.Match) -> str:
        """Make pre-NotebookLM answers clickable too, based on source chunk metadata."""
        source_name, detail = match.group(1).strip(), match.group(2)
        original_indices = [int(value) for value in re.findall(r"chunk\s+(\d+)", detail, flags=re.IGNORECASE)]
        ui_indices = [
            position + 1 for position, item in enumerate(sources)
            if item.get("metadata", {}).get("source") == source_name
            and item.get("metadata", {}).get("chunk_index") in original_indices
        ]
        return " ".join(f"[chunk{index}]" for index in ui_indices) or match.group(0)

    answer = re.sub(r"\[Source:\s*([^\]|]+)\|\s*([^\]]+)\]", legacy_citation_to_chunks, answer)

    def citation_tooltip(match: re.Match) -> str:
        label = match.group(0)
        chunk_number = int(match.group(1))
        if chunk_number < 1 or chunk_number > len(sources):
            return html.escape(label)
        item = sources[chunk_number - 1]
        source_name = str(item.get("metadata", {}).get("source", "Unknown source"))
        excerpt = " ".join(item.get("content", "").split())
        target = f"{anchor_prefix}-chunk{chunk_number}"
        # Keep long evidence in an element, never an HTML attribute: document
        # text can contain quotes and markup-like characters that break title="...".
        return (f'<a class="citation-tooltip" href="#{target}">{html.escape(label)}'
                f'<span class="citation-popup"><strong>{html.escape(source_name)}</strong><br>'
                f'{html.escape(excerpt)}</span></a>')

    # Escape all model output first. Brackets survive escaping, so only genuine citation
    # labels are then replaced with our controlled HTML.
    safe_answer = html.escape(answer).replace("\n", "<br>")
    return re.sub(r"\[chunk(\d+)\]", citation_tooltip, safe_answer, flags=re.IGNORECASE)


def render_source_chunk(source: dict, chunk_number: int, anchor_prefix: str) -> str:
    """Create the click destination for one cited chunk."""
    metadata = source.get("metadata", {})
    source_name = html.escape(str(metadata.get("source", "Unknown source")))
    doc_type = html.escape(str(metadata.get("type", "unknown")))
    score = float(source.get("score", 0))
    content = html.escape(source.get("content", ""))
    anchor = f"{anchor_prefix}-chunk{chunk_number}"
    return f'''<div id="{anchor}" class="source-chunk">
<strong>[chunk{chunk_number}] {source_name}</strong> <code>{doc_type}</code> | score: <code>{score:.4f}</code>
<div class="source-content">{content}</div>
</div>'''

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Book Insights RAG Chatbot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """<style>
    .citation-tooltip { color: #4da3ff; font-weight: 600; cursor: pointer;
      border-bottom: 1px dotted #4da3ff; text-decoration: none; position: relative; }
    .citation-popup { visibility: hidden; opacity: 0; position: absolute; z-index: 9999;
      left: 0; bottom: 1.6rem; width: min(44rem, 75vw); max-height: 18rem; overflow-y: auto;
      padding: .75rem; border: 1px solid #4da3ff; border-radius: .4rem; color: #f5f5f5;
      background: #17202b; box-shadow: 0 4px 18px rgba(0,0,0,.45); white-space: pre-wrap;
      font-weight: normal; line-height: 1.45; transition: opacity .15s; pointer-events: none; }
    .citation-tooltip:hover .citation-popup, .citation-tooltip:focus .citation-popup {
      visibility: visible; opacity: 1; }
    .source-chunk { scroll-margin-top: 1rem; padding: .75rem 1rem; margin: .5rem 0;
      border-left: 3px solid #4da3ff; border-radius: .25rem; }
    .source-chunk:target { background: rgba(77, 163, 255, .18); animation: citation-flash 2s ease-out; }
    .source-content { white-space: pre-wrap; margin-top: .75rem; line-height: 1.55; }
    @keyframes citation-flash { from { background: rgba(255, 190, 60, .45); } to { background: rgba(77, 163, 255, .18); } }
    </style>""",
    unsafe_allow_html=True,
)

# =============================================================================
# SIDEBAR — INFO & SETTINGS
# =============================================================================

with st.sidebar:
    st.title("📚 Book Insights RAG")
    st.caption("Trợ lý review, tóm tắt và phân tích sách về phát triển bản thân, kinh doanh, tâm lý học và công nghệ")

    st.divider()

    st.subheader("💡 Câu hỏi gợi ý")
    suggestions = [
        "Phương pháp 4 bước xây dựng thói quen theo Atomic Habits là gì?",
        "Bốn quy luật thay đổi hành vi trong Atomic Habits là gì?",
        "MVP được Lean Startup sử dụng để làm gì?",
        "Vòng lặp Build-Measure-Learn hoạt động như thế nào?",
        "Hệ thống 1 và Hệ thống 2 trong Thinking, Fast and Slow khác nhau thế nào?",
        "Điểm yếu của System 2 theo Thinking, Fast and Slow là gì?",
        "The Innovators nói về lịch sử đổi mới công nghệ như thế nào?",
    ]
    for s in suggestions:
        if st.button(s, use_container_width=True, key=f"sug_{s[:20]}"):
            st.session_state["pending_query"] = s

    if st.button("🗑️ Xóa hội thoại", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_query = None
        st.rerun()

    st.divider()
    st.subheader("⚙️ Thiết lập")
    top_k = st.slider("Số chunks retrieval (top_k)", 3, 10, 5)
    st.caption(f"LLM: `{os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')}`")
    st.caption(f"Base URL: `{os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')}`")

    st.divider()
    st.caption("**Kiến trúc hệ thống:**")
    st.caption("Hybrid Retrieval (Semantic + BM25) → RRF Rerank → PageIndex Fallback → LLM Generation có Citation")
    st.caption("💡 Click `[chunkN]` trong câu trả lời để xem evidence tương ứng.")

# =============================================================================
# SESSION STATE
# =============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# =============================================================================
# MAIN CHAT AREA
# =============================================================================

st.title("📚 Trợ Lý Review & Tóm Tắt Sách")
st.caption("Hệ thống hỏi đáp và phân tích sách với trích dẫn từ nguồn đã được cung cấp")

# Hiển thị lịch sử chat
for message_index, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            anchor_prefix = f"answer-{message_index}"
            st.markdown(render_answer_with_citation_tooltips(msg["content"], msg.get("sources", []), anchor_prefix), unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])
        if msg["role"] == "assistant" and "sources" in msg and msg["sources"]:
            with st.expander(f"📚 Nguồn tham khảo ({len(msg['sources'])} chunks)", expanded=True):
                for i, src in enumerate(msg["sources"], 1):
                    st.markdown(render_source_chunk(src, i, anchor_prefix), unsafe_allow_html=True)

# =============================================================================
# QUERY HANDLING
# =============================================================================

# Xử lý khi bấm nút gợi ý hoặc nhập câu hỏi mới
user_input = st.chat_input("Nhập câu hỏi về nội dung, bài học hoặc góc nhìn từ sách...")
query = user_input or st.session_state.pending_query

if query:
    st.session_state.pending_query = None

    # Hiển thị câu hỏi của user
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Sinh câu trả lời từ RAG Pipeline
    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm tài liệu và tổng hợp câu trả lời..."):
            try:
                from src.supervisor import PipelineSupervisor
                response = PipelineSupervisor().answer(query, top_k=top_k)
                answer = response.get("answer", "Chưa thể trả lời.")
                sources = response.get("sources", [])

            except NotImplementedError:
                answer = "⚠️ **Task 10 chưa được implement.** Hãy hoàn thành `src/task10_generation.py` để kết nối pipeline vào UI!"
                sources = []
            except Exception as e:
                answer = f"❌ **Lỗi khi chạy RAG Pipeline:** {e}"
                sources = []

            anchor_prefix = f"answer-{len(st.session_state.messages)}"
            st.markdown(render_answer_with_citation_tooltips(answer, sources, anchor_prefix), unsafe_allow_html=True)

            if sources:
                with st.expander(f"📚 Nguồn tham khảo ({len(sources)} chunks)", expanded=True):
                    for i, src in enumerate(sources, 1):
                        st.markdown(render_source_chunk(src, i, anchor_prefix), unsafe_allow_html=True)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
    })
