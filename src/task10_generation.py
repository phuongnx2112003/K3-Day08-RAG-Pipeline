"""
Task 10 — Generation Có Citation.

Hướng dẫn:
    1. Chọn top_k, top_p phù hợp (giải thích lý do)
    2. Sắp xếp lại chunks sau reranking để tránh "lost in the middle"
    3. Inject context vào prompt
    4. Yêu cầu LLM trả lời có citation
    5. Nếu không đủ evidence → "I cannot verify this information"

Gợi ý LLM: OpenRouter có nhiều model gắn hậu tố ":free" không tính phí — xem
https://openrouter.ai/models?max_price=0 — phù hợp nếu chưa có credit trả phí.
Base URL: "https://openrouter.ai/api/v1", dùng chung interface với OpenAI SDK.
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from .task9_retrieval_pipeline import retrieve
except ImportError:
    retrieve = None
from pathlib import Path
import re


# =============================================================================
# CONFIGURATION — Giải thích lựa chọn
# =============================================================================

# top_k: Số chunks đưa vào context
# Chọn 5 vì: đủ evidence mà không quá dài gây lost in the middle
TOP_K = 5

# top_p (nucleus sampling): Xác suất tích luỹ cho token generation
# Chọn 0.9 vì: đủ diverse nhưng không quá random
TOP_P = 0.9

# temperature: Độ ngẫu nhiên của output
# Chọn 0.3 vì: RAG cần factual, ít sáng tạo
TEMPERATURE = 0.3

# TODO: Chọn LLM model (OpenRouter model ID)
LLM_MODEL = "openai/gpt-4o-mini"  # hoặc model ":free" nếu chưa có credit


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """Bạn là trợ lý review và tóm tắt sách chuyên sâu về phát triển
bản thân, kinh doanh, tâm lý học và công nghệ.

Quy tắc bắt buộc:
1. Chỉ sử dụng thông tin từ context được cung cấp — KHÔNG bịa đặt
2. Mỗi khẳng định phải có trích dẫn ngay sau, ví dụ: [Atomic Habits - Chương 1]
3. Nếu context không đủ thông tin → trả lời: "Tôi không thể xác minh thông tin này từ nguồn hiện có"
4. Trả lời bằng tiếng Việt, có cấu trúc rõ ràng theo đoạn văn
5. Phân biệt rõ nội dung được nguồn nêu trực tiếp với phần tổng hợp từ nhiều nguồn
6. Không suy luận hay mở rộng ngoài những gì được nêu trong context"""


# =============================================================================
# DOCUMENT REORDERING (tránh lost in the middle)
# =============================================================================

def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """
    Sắp xếp chunks để tránh "lost in the middle" effect.

    LLM nhớ tốt thông tin ở ĐẦU và CUỐI prompt, quên thông tin ở GIỮA.
    Strategy: đặt chunks quan trọng nhất ở đầu và cuối, kém quan trọng ở giữa.

    Input order (by score):  [1, 2, 3, 4, 5]
    Output order:            [1, 3, 5, 4, 2]
    (best first, worst in middle, second-best last)

    Args:
        chunks: List sorted by score descending (from retrieval)

    Returns:
        List reordered để maximize LLM attention.
    """
    if len(chunks) <= 2:
        return chunks

    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


# =============================================================================
# CONTEXT FORMATTING
# =============================================================================


def format_context(chunks: list[dict]) -> str:
    """
    Format chunks thành context string cho prompt.
    Mỗi chunk có label source để LLM có thể cite.

    Args:
        chunks: List of {'content': str, 'metadata': dict, 'score': float}

    Returns:
        Formatted context string.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        source = metadata.get("source", f"Source {i}")
        doc_type = metadata.get("type", "unknown")
        content = chunk.get("content", "").strip()
        context_parts.append(
            f"[Document {i} | Source: {source} | Type: {doc_type}]\n"
            f"{content}"
        )
    return "\n---\n".join(context_parts)


# =============================================================================
# LOCAL RETRIEVAL FALLBACK
# =============================================================================


STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


def retrieve_local(query: str, top_k: int = TOP_K) -> list[dict]:
    """Fallback retrieval từ các tài liệu markdown sẵn có khi pipeline chính chưa sẵn sàng."""
    if not query.strip():
        return []

    query_terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]
    if not query_terms:
        return []

    candidates: list[dict] = []
    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        if md_file.name.startswith("."):
            continue
        text = md_file.read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        for idx, paragraph in enumerate(paragraphs):
            paragraph_lower = paragraph.lower()
            score = sum(paragraph_lower.count(term) for term in query_terms)
            if score <= 0:
                continue
            doc_type = "legal" if "legal" in str(md_file.parent).lower() else "news"
            candidates.append({
                "content": paragraph,
                "score": float(score),
                "metadata": {
                    "source": md_file.name,
                    "type": doc_type,
                    "chunk_index": idx,
                },
                "source": "local",
            })

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:top_k]


def _render_fallback_answer(chunks: list[dict], query: str) -> str:
    if not chunks:
        return (
            "Tôi không thể xác minh thông tin này từ nguồn hiện có. "
            "Vui lòng thử lại với câu hỏi cụ thể hơn."
        )

    top_chunk = chunks[0]
    metadata = top_chunk.get("metadata", {})
    source = metadata.get("source", "Unknown")
    summary = top_chunk.get("content", "").strip()
    return (
        f"Dựa trên nguồn tham khảo, câu trả lời sơ bộ là:\n\n"
        f"{summary[:420].rstrip()}...\n\n"
        f"[Citation: {source}]"
    )


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """
    End-to-end RAG generation có citation.

    Pipeline:
        1. Retrieve relevant chunks
        2. Reorder để tránh lost in the middle
        3. Format context với source labels
        4. Build prompt (system + context + query)
        5. Call LLM nếu có API key
        6. Return answer + sources

    Args:
        query: Câu hỏi của user

    Returns:
        {
            'answer': str,           # Câu trả lời có citation
            'sources': list[dict],   # Các chunks đã dùng
            'retrieval_source': str  # 'hybrid' hoặc 'pageindex' hoặc 'local'
        }
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a non-empty string")

    # Step 1: Retrieve via Task 9 if available, otherwise fallback to local retrieval.
    chunks: list[dict] = []
    if callable(retrieve):
        try:
            chunks = retrieve(query, top_k=top_k)
        except NotImplementedError:
            chunks = []
        except Exception:
            chunks = []

    retrieval_source = "hybrid"
    if not chunks:
        chunks = retrieve_local(query, top_k=top_k)
        retrieval_source = "local"
    elif chunks and all(item.get("source") == "local" for item in chunks):
        retrieval_source = "local"
    else:
        retrieval_source = chunks[0].get("source", "hybrid")

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)

    answer = None
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key and chunks:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
            user_message = f"Context:\n{context}\n\n---\n\nQuestion: {query}"
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=TEMPERATURE,
                top_p=TOP_P,
            )
            answer = response.choices[0].message.content.strip()
        except Exception:
            answer = None

    if not answer:
        answer = _render_fallback_answer(chunks, query)

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }

if __name__ == "__main__":
    test_queries = [
        "Phương pháp 4 bước xây dựng thói quen theo Atomic Habits là gì?",
        "Deep Work đề xuất cách nào để giảm xao nhãng?",
        "Hệ thống 1 và Hệ thống 2 khác nhau thế nào?",
    ]

    for q in test_queries:
        print(f"\n{'='*70}")
        print(f"Q: {q}")
        print("=" * 70)
        result = generate_with_citation(q)
        print(f"\nA: {result['answer']}")
        print(f"\n[Sources: {len(result['sources'])} chunks | via {result['retrieval_source']}]")
