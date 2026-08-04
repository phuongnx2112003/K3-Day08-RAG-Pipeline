"""Task 10 — sinh câu trả lời RAG có citation được kiểm chứng."""

from __future__ import annotations

import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

try:
    from .task9_retrieval_pipeline import retrieve
except ImportError:  # pragma: no cover - hỗ trợ chạy trực tiếp module
    retrieve = None


TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
REFUSAL_MESSAGE = "Tôi không thể xác minh thông tin này từ nguồn hiện có."
_CITATION_RE = re.compile(r"\[S(\d+)\]")

SYSTEM_PROMPT = """You are an evidence-grounded assistant.
Answer only from the supplied context. Cite every material claim using the
provided [S#] identifiers. If evidence is insufficient, use the configured
Vietnamese refusal message exactly."""


def is_vietnamese(text: str) -> bool:
    """Return whether input contains Vietnamese-specific characters."""

    return bool(re.search(r"[àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", text.lower()))


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Place highly-ranked chunks at both the beginning and end of context."""

    if len(chunks) <= 2:
        return list(chunks)
    return chunks[::2] + chunks[1::2][::-1]


def prepare_citation_sources(chunks: list[dict]) -> list[dict]:
    """Copy chunks and give each prompt source a stable, one-based citation ID."""

    prepared: list[dict] = []
    for index, chunk in enumerate(chunks, start=1):
        item = dict(chunk)
        metadata = dict(item.get("metadata") or {})
        metadata["citation_id"] = f"S{index}"
        item["metadata"] = metadata
        prepared.append(item)
    return prepared


def format_context(chunks: list[dict]) -> str:
    """Render retrieved chunks with the exact citation IDs available to the LLM."""

    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.get("metadata") or {}
        citation_id = metadata.get("citation_id", f"S{index}")
        source = metadata.get("source", f"Source {index}")
        doc_type = metadata.get("type", "unknown")
        content = str(chunk.get("content", "")).strip()
        parts.append(f"[{citation_id}] Source: {source} | Type: {doc_type}\n{content}")
    return "\n---\n".join(parts)


def validate_citations(answer: str, source_count: int) -> tuple[bool, list[str]]:
    """Ensure every [S#] emitted by the model identifies a supplied source."""

    if answer == REFUSAL_MESSAGE:
        return True, []
    invalid = [f"S{number}" for number in _CITATION_RE.findall(answer) if not 1 <= int(number) <= source_count]
    return not invalid, invalid


def _openai_answer(query: str, context: str) -> str | None:
    """Call a configured OpenAI-compatible endpoint, or return ``None`` offline."""

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not openai_key and not openrouter_key:
        return None

    from openai import OpenAI

    if openai_key:
        client = OpenAI(api_key=openai_key)
    else:
        client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ],
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )
    content = response.choices[0].message.content
    return content.strip() if content else None


def generate_with_citation(
    query: str,
    top_k: int = TOP_K,
    retrieval_mode: str = "hybrid",
    use_reranking: bool = True,
    use_pageindex_fallback: bool = True,
    *,
    conversation: list[dict[str, Any]] | None = None,
    score_threshold: float | None = None,
) -> dict:
    """Retrieve evidence, generate an answer, and return validated citations.

    ``conversation`` is accepted for UI compatibility; the current prompt remains
    single-turn to avoid injecting unverified chat history. ``score_threshold`` is
    forwarded to Task 9 when supplied.
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a non-empty string")

    retrieval_kwargs: dict[str, Any] = {
        "top_k": top_k,
        "retrieval_mode": retrieval_mode,
        "use_reranking": use_reranking,
        "use_pageindex_fallback": use_pageindex_fallback,
    }
    if score_threshold is not None:
        retrieval_kwargs["score_threshold"] = score_threshold

    chunks: list[dict] = []
    if callable(retrieve):
        try:
            chunks = retrieve(query, **retrieval_kwargs)
        except Exception:
            chunks = []

    if not chunks:
        return {
            "answer": REFUSAL_MESSAGE,
            "sources": [],
            "retrieval_source": "none",
            "model": None,
            "citations_valid": True,
            "invalid_citations": [],
        }

    sources = prepare_citation_sources(reorder_for_llm(chunks))
    context = format_context(sources)
    try:
        answer = _openai_answer(query, context)
    except Exception:
        answer = None
    if not answer:
        answer = REFUSAL_MESSAGE

    citations_valid, invalid_citations = validate_citations(answer, len(sources))
    return {
        "answer": answer,
        "sources": sources,
        "retrieval_source": retrieval_mode,
        "model": LLM_MODEL if answer != REFUSAL_MESSAGE else None,
        "citations_valid": citations_valid,
        "invalid_citations": invalid_citations,
    }
