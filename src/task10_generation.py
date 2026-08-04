"""
Task 10 — Generation Có Citation (Hỗ trợ cấu hình Config A & Config B cho A/B Testing).

Hướng dẫn:
    1. Chọn top_k, top_p phù hợp
    2. Sắp xếp lại chunks sau reranking để tránh "lost in the middle"
    3. Inject context vào prompt
    4. Yêu cầu LLM trả lời có citation
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    from .task9_retrieval_pipeline import retrieve
except ImportError:
    retrieve = None

# =============================================================================
# CONFIGURATION
# =============================================================================

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# =============================================================================
# SYSTEM PROMPT (Multi-lingual support: EN & VI)
# =============================================================================

SYSTEM_PROMPT = """You are an expert AI Book Assistant specializing in personal development, business, psychology, and technology books.

Mandatory Rules:
1. LANGUAGE MATCHING: Respond in the EXACT SAME LANGUAGE as the user's query. If the query is in Vietnamese, respond in clear Vietnamese. If the query is in English, respond in professional English.
2. CITATION REQUIREMENT: Support claims with exact source citations immediately following the point, e.g., [Atomic Habits - Chapter 1] or [article_01.md].
3. FACTUAL BOUNDARY: Rely ONLY on the provided context. Do NOT fabricate facts.
4. INSUFFICIENT EVIDENCE: If context lacks sufficient evidence, state clearly: "I cannot verify this information from the available sources" (or "Tôi không thể xác minh thông tin này từ nguồn hiện có" if in Vietnamese).
5. Structure your response clearly with concise bullet points or paragraphs."""


def is_vietnamese(text: str) -> bool:
    """Kiểm tra xem câu hỏi có chứa ký tự tiếng Việt hay không."""
    vietnamese_chars = r'[àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]'
    return bool(re.search(vietnamese_chars, text.lower()))


# =============================================================================
# DOCUMENT REORDERING (tránh lost in the middle)
# =============================================================================

def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """
    Sắp xếp chunks để tránh "lost in the middle" effect.
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
    """Fallback retrieval từ các tài liệu markdown sẵn có."""
    if not query.strip():
        return []

    query_terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]
    if not query_terms:
        return []

    candidates: list[dict] = []
    if STANDARDIZED_DIR.exists():
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
    vi = is_vietnamese(query)
    if not chunks:
        return (
            "Tôi không thể xác minh thông tin này từ nguồn hiện có."
            if vi else
            "I cannot verify this information from the available sources."
        )

    parts = [
        "📌 **Tổng hợp tri thức từ tài liệu trích xuất (RAG Pipeline)**:\n" if vi
        else "📌 **Synthesized knowledge from retrieved chunks (RAG Pipeline)**:\n"
    ]

    for i, c in enumerate(chunks[:3], 1):
        src = c.get("metadata", {}).get("source", "Sách")
        text = c.get("content", "").strip().replace("\n", " ")
        if len(text) > 280:
            text = text[:280] + "..."
        parts.append(f"• **Điểm {i}** `[{src}]`: {text}\n")

    if vi:
        parts.append("\n⚠️ *(Lưu ý: Thêm OPENAI_API_KEY vào .env để kích hoạt AI trả lời mượt mà)*")
    else:
        parts.append("\n⚠️ *(Note: Add OPENAI_API_KEY to .env for full AI generation)*")

    return "\n".join(parts)


def generate_with_citation(
    query: str,
    top_k: int = TOP_K,
    retrieval_mode: str = "hybrid",
    use_reranking: bool = True,
    use_pageindex_fallback: bool = True
) -> dict:
    """
    End-to-end RAG generation hỗ trợ các cấu hình A/B Retrieval:
    - Config A: retrieval_mode="hybrid", use_reranking=True, use_pageindex_fallback=True
    - Config B: retrieval_mode="dense_only", use_reranking=False, use_pageindex_fallback=False
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a non-empty string")

    chunks: list[dict] = []
    if callable(retrieve):
        try:
            chunks = retrieve(
                query,
                top_k=top_k,
                retrieval_mode=retrieval_mode,
                use_reranking=use_reranking,
                use_pageindex_fallback=use_pageindex_fallback
            )
        except Exception:
            chunks = []

    retrieval_source = retrieval_mode
    if not chunks:
        chunks = retrieve_local(query, top_k=top_k)
        retrieval_source = "local"

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)

    answer = None
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()

    if chunks:
        try:
            from openai import OpenAI

            client = None
            model_to_use = LLM_MODEL

            if openai_key and not openai_key.startswith("sk-or-v1"):
                client = OpenAI(api_key=openai_key)
            elif openrouter_key and not openrouter_key.startswith("sk-or-v1-..."):
                client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")

            if client is not None:
                lang_instruction = "Respond in Vietnamese." if is_vietnamese(query) else "Respond in English."
                user_message = f"Language Requirement: {lang_instruction}\n\nContext:\n{context}\n\n---\n\nQuestion: {query}"
                response = client.chat.completions.create(
                    model=model_to_use,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                )
                answer = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM Call Error: {e}")
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
    ]

    for q in test_queries:
        print(f"\n{'='*70}\nQ: {q}\n" + "="*70)
        res_a = generate_with_citation(q, config_type="A")
        print(f"\nConfig A Answer: {res_a['answer']}")
