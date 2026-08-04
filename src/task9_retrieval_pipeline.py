"""Task 9 — Hybrid retrieval + RRF + PageIndex fallback."""

from __future__ import annotations

from typing import Literal

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import (
    PAGEINDEX_API_KEY,
    RECOMMENDED_FALLBACK_THRESHOLD,
    get_registered_doc_ids,
    pageindex_search,
    should_fallback,
)


SCORE_THRESHOLD = RECOMMENDED_FALLBACK_THRESHOLD
DEFAULT_TOP_K = 5
RRF_K = 60
RetrievalMode = Literal["hybrid", "dense_only", "sparse_only"]


def _chunk_identity(item: dict) -> tuple[str, ...]:
    metadata = item.get("metadata") or {}
    if metadata.get("source") is not None and metadata.get("chunk_index") is not None:
        return ("chunk", str(metadata["source"]), str(metadata["chunk_index"]))
    return ("content", str(item.get("content", "")))


def _merge_without_rrf(*ranked_lists: list[dict], top_k: int) -> list[dict]:
    """Merge ổn định, ưu tiên list đứng trước và loại chunk trùng."""

    output: list[dict] = []
    seen: set[tuple[str, ...]] = set()
    for ranked_list in ranked_lists:
        for item in ranked_list:
            key = _chunk_identity(item)
            if key in seen:
                continue
            seen.add(key)
            output.append(item.copy())
            if len(output) >= top_k:
                return output
    return output


def _mark_results(
    results: list[dict],
    *,
    retrieval_mode: str,
    best_dense_score: float,
) -> list[dict]:
    output: list[dict] = []
    for item in results:
        copied = item.copy()
        metadata = dict(copied.get("metadata") or {})
        metadata["retrieval_mode"] = retrieval_mode
        metadata["best_dense_score"] = round(best_dense_score, 4)
        copied["metadata"] = metadata
        copied["source"] = "hybrid"
        output.append(copied)
    return output


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
    *,
    retrieval_mode: RetrievalMode = "hybrid",
    use_pageindex_fallback: bool = True,
) -> list[dict]:
    """Chạy retrieval và trả contract chung cho Task 10/UI.

    Fallback chỉ dựa trên cosine gốc cao nhất của dense search. Nếu PageIndex không
    tìm thấy evidence, hàm trả ``[]`` thay vì chuyển tiếp các chunks hybrid yếu.
    """

    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not query.strip():
        return []
    if not isinstance(top_k, int):
        raise TypeError("top_k must be an integer")
    if top_k <= 0:
        return []
    if not 0.0 <= score_threshold <= 1.0:
        raise ValueError("score_threshold must be between 0 and 1")
    if retrieval_mode not in ("hybrid", "dense_only", "sparse_only"):
        raise ValueError("retrieval_mode must be hybrid, dense_only, or sparse_only")

    candidate_k = max(top_k * 2, top_k)
    dense_results = (
        semantic_search(query, top_k=candidate_k)
        if retrieval_mode in ("hybrid", "dense_only")
        else []
    )
    sparse_results = (
        lexical_search(query, top_k=candidate_k)
        if retrieval_mode in ("hybrid", "sparse_only")
        else []
    )
    best_dense_score = max(
        (float(item.get("score", 0.0)) for item in dense_results),
        default=0.0,
    )

    # Sparse-only không có cosine để hiệu chỉnh, nên không tự gọi PageIndex.
    can_check_fallback = retrieval_mode in ("hybrid", "dense_only")
    pageindex_available = bool(get_registered_doc_ids()) and bool(
        PAGEINDEX_API_KEY and "..." not in PAGEINDEX_API_KEY
    )
    if (
        use_pageindex_fallback
        and can_check_fallback
        and pageindex_available
        and should_fallback(dense_results, score_threshold)
    ):
        fallback = pageindex_search(query, top_k=top_k)
        if fallback:
            return fallback[:top_k]
        # Không có evidence từ fallback thì phải từ chối, thay vì đưa context
        # dense dưới ngưỡng vào generation.
        # Fallback returned no evidence; continue.

    if retrieval_mode == "dense_only":
        selected = dense_results[:top_k]
    elif retrieval_mode == "sparse_only":
        selected = sparse_results[:top_k]
    elif use_reranking:
        selected = rerank_rrf(
            [dense_results, sparse_results],
            top_k=top_k,
            k=RRF_K,
        )
    else:
        selected = _merge_without_rrf(dense_results, sparse_results, top_k=top_k)

    return _mark_results(
        selected[:top_k],
        retrieval_mode=retrieval_mode,
        best_dense_score=best_dense_score,
    )


if __name__ == "__main__":
    test_queries = [
        "What are the four laws of behavior change in Atomic Habits?",
        "Explain System 1 and System 2 in Thinking Fast and Slow.",
        "What is the current Bitcoin price today?",
    ]
    for question in test_queries:
        print(f"\nQuery: {question}")
        for rank, result in enumerate(retrieve(question, top_k=3), start=1):
            print(
                f"  {rank}. [{result['score']:.4f}] [{result['source']}] "
                f"{result['content'][:90]}..."
            )
