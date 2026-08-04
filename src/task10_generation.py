"""Task 10 — generate grounded answers with verifiable citations.

This module consumes the common result contract returned by Task 9.  It never
uses a local retrieval fallback: when Task 9 cannot find evidence (including
after its PageIndex fallback), the safe result is a refusal rather than an
unsupported answer.
"""

from __future__ import annotations

import os
import re
from typing import Any, Sequence

from dotenv import load_dotenv

try:
    # Keep Task 10 importable for its pure helpers even when optional retrieval
    # dependencies (for example ChromaDB) have not yet been installed.
    from .task9_retrieval_pipeline import retrieve
except ImportError:  # pragma: no cover - depends on optional local packages
    retrieve = None


load_dotenv()

# Five chunks usually provide enough supporting evidence without making the
# context unnecessarily long.  Low temperature keeps a RAG answer factual;
# top_p=0.9 still allows natural Vietnamese phrasing.
TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
LLM_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
REFUSAL_MESSAGE = "I cannot verify this information."

SYSTEM_PROMPT = """You are a careful Vietnamese RAG assistant.
Answer only from the supplied context. Every factual claim must include the
matching source citation in the form [S1], [S2], and so on. Do not invent a
citation or use outside knowledge. If the context does not explicitly support
the answer, reply exactly: I cannot verify this information.
Write the answer in Vietnamese when evidence is available."""

_CITATION_RE = re.compile(r"\[S(\d+)\]")


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Put high-ranked chunks at the beginning and end of the prompt.

    For ranked ``[1, 2, 3, 4, 5]`` this returns ``[1, 3, 5, 4, 2]``.  This
    ``front + back[::-1]`` pattern mitigates the lost-in-the-middle effect
    while preserving every chunk exactly once.
    """
    if len(chunks) <= 2:
        return list(chunks)
    return list(chunks[::2]) + list(chunks[1::2])[::-1]


def prepare_citation_sources(chunks: Sequence[dict]) -> list[dict]:
    """Copy chunks and attach stable citation IDs (``S1``, ``S2``, ...)."""
    prepared: list[dict] = []
    for index, chunk in enumerate(chunks, start=1):
        item = dict(chunk)
        metadata = dict(item.get("metadata") or {})
        metadata["citation_id"] = f"S{index}"
        metadata.setdefault("display_source", metadata.get("source", f"Source {index}"))
        item["metadata"] = metadata
        prepared.append(item)
    return prepared


def format_context(chunks: Sequence[dict]) -> str:
    """Render chunks with the exact IDs the model must use as citations."""
    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.get("metadata") or {}
        citation_id = metadata.get("citation_id", f"S{index}")
        source = metadata.get("display_source") or metadata.get("source", f"Source {index}")
        doc_type = metadata.get("type", "unknown")
        content = str(chunk.get("content", "")).strip()
        if content:
            parts.append(f"[{citation_id}] Source: {source} | Type: {doc_type}\n{content}")
    return "\n\n---\n\n".join(parts)


def validate_citations(answer: str, source_count: int) -> tuple[bool, list[str]]:
    """Return whether all ``[S<n>]`` citations refer to supplied sources."""
    if answer.strip() == REFUSAL_MESSAGE:
        return (source_count == 0, [])
    cited = _CITATION_RE.findall(answer)
    invalid = [f"S{number}" for number in cited if not 1 <= int(number) <= source_count]
    # Evidence-backed answers must actually cite at least one available source.
    if source_count and not cited:
        invalid.append("missing citation")
    return (not invalid, invalid)


def _conversation_text(conversation: Sequence[dict] | None) -> str:
    if not conversation:
        return ""
    lines: list[str] = []
    for message in conversation[-6:]:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "user"))
        content = str(message.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _openai_answer(query: str, context: str, conversation: Sequence[dict] | None = None) -> str | None:
    """Call OpenRouter/OpenAI when configured; return ``None`` on failure."""
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openrouter_key and not openai_key:
        return None

    try:
        from openai import OpenAI

        if openrouter_key:
            client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
            model = LLM_MODEL
        else:
            client = OpenAI(api_key=openai_key)
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        history = _conversation_text(conversation)
        history_section = f"Previous conversation (do not treat as evidence):\n{history}\n\n" if history else ""
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\n{history_section}Question: {query}",
                },
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception:
        return None


def generate_with_citation(
    query: str,
    top_k: int = TOP_K,
    *,
    conversation: Sequence[dict] | None = None,
    score_threshold: float | None = None,
) -> dict[str, Any]:
    """Retrieve with Task 9, reorder context, then produce cited output.

    The returned ``sources`` are in the same order as the context and carry
    the ``citation_id`` referenced in the answer.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer")

    retrieval_args: dict[str, Any] = {"top_k": top_k}
    if score_threshold is not None:
        retrieval_args["score_threshold"] = score_threshold
    try:
        retrieved = retrieve(query, **retrieval_args) if callable(retrieve) else []
    except Exception:
        retrieved = []

    sources = prepare_citation_sources(reorder_for_llm(retrieved))
    retrieval_source = sources[0].get("source", "hybrid") if sources else "none"
    if not sources:
        return {
            "answer": REFUSAL_MESSAGE,
            "sources": [],
            "retrieval_source": retrieval_source,
            "citations_valid": True,
            "invalid_citations": [],
            "model": None,
        }

    answer = _openai_answer(query, format_context(sources), conversation)
    if not answer:
        answer = REFUSAL_MESSAGE
    citations_valid, invalid_citations = validate_citations(answer, len(sources))
    if not citations_valid:
        answer = REFUSAL_MESSAGE
        citations_valid, invalid_citations = validate_citations(answer, 0)

    return {
        "answer": answer,
        "sources": sources,
        "retrieval_source": retrieval_source,
        "citations_valid": citations_valid,
        "invalid_citations": invalid_citations,
        "model": LLM_MODEL if answer != REFUSAL_MESSAGE else None,
    }


<<<<<<< HEAD
    for q in test_queries:
        print(f"\n{'='*70}")
        print(f"Q: {q}")
        print("=" * 70)
        result = generate_with_citation(q)
        print(f"\nA: {result['answer']}")
        print(f"\n[Sources: {len(result['sources'])} chunks | via {result['retrieval_source']}]")
=======
if __name__ == "__main__":
    result = generate_with_citation("What are the four laws of behavior change?")
    print(result["answer"])
>>>>>>> 402e1e6ad54f8511a8940733b2e9f70c6b62af7a
