"""Task 9 — hybrid retrieval, Jina reranking, and PageIndex fallback."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank, rerank_rrf
from .task8_pageindex_vectorless import pageindex_search
from .query_preprocessing import expand_query, normalize_query

SCORE_THRESHOLD = 0.3
DEFAULT_TOP_K = 5
RERANK_METHOD = "cross_encoder"


def retrieve(query: str, top_k: int = DEFAULT_TOP_K, score_threshold: float = SCORE_THRESHOLD,
             use_reranking: bool = True) -> list[dict]:
    """Retrieve evidence. The fallback decision uses raw dense similarity, never RRF."""
    query = normalize_query(query)
    if not query or top_k <= 0:
        return []
    variants = expand_query(query)
    with ThreadPoolExecutor(max_workers=max(2, len(variants) * 2)) as executor:
        jobs = [(variant, executor.submit(semantic_search, variant, top_k * 2),
                 executor.submit(lexical_search, variant, top_k * 2)) for variant in variants]
        dense_lists, lexical_lists = [], []
        for _variant, dense_job, lexical_job in jobs:
            try:
                dense_lists.append(dense_job.result())
            except Exception:
                dense_lists.append([])
            try:
                lexical_lists.append(lexical_job.result())
            except Exception:
                lexical_lists.append([])

    dense = [item for result_list in dense_lists for item in result_list]
    lexical = [item for result_list in lexical_lists for item in result_list]

    # Use the unmodified cosine score for the fallback calibration.
    best_dense_score = float(dense[0]["score"]) if dense else 0.0
    merged = rerank_rrf([*dense_lists, *lexical_lists], top_k=top_k * 2)
    for item in merged:
        item["source"] = "hybrid"
    if best_dense_score < score_threshold:
        fallback = pageindex_search(query, top_k=top_k)
        if fallback:
            return fallback
    if not merged:
        return []
    rerank_query = variants[1] if len(variants) > 1 else query
    final = rerank(rerank_query, merged, top_k=top_k, method=RERANK_METHOD) if use_reranking else merged[:top_k]
    return [{**item, "source": item.get("source", "hybrid"), "metadata": {**item.get("metadata", {}), "query_variants": variants}}
            for item in final[:top_k]]
