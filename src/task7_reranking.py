"""
Task 7 — Reranking Module.

Chọn 1 trong các phương pháp:
    - Cross-encoder reranker: Jina Reranker v2 (multilingual) hoặc Qwen3-Reranker
    - MMR (Maximal Marginal Relevance): tự implement
    - RRF (Reciprocal Rank Fusion): tự implement — khuyến nghị vì không cần API key

Nếu dùng MMR hoặc RRF, đảm bảo hiểu và giải thích được cơ chế.

Lưu ý quan trọng về RRF (sẽ dùng lại ở Task 9): điểm RRF fused CHỈ phụ thuộc thứ hạng,
không phải độ tương đồng thật. Top-1 sau khi fuse luôn xấp xỉ 1/(k+1) ≈ 0.0164 (k=60),
bất kể nội dung đó có thật sự liên quan đến câu hỏi hay không. Đừng dùng điểm RRF để
quyết định fallback ở Task 9 — xem ghi chú ở đó.
"""

from __future__ import annotations

from typing import Any


def rerank_cross_encoder(
    query: str, candidates: list[dict], top_k: int = 5
) -> list[dict]:
    """
    Rerank candidates sử dụng cross-encoder model.

    Args:
        query: Câu truy vấn
        candidates: List of {'content': str, 'score': float, 'metadata': dict}
        top_k: Số lượng kết quả sau rerank

    Returns:
        List of top_k candidates, re-scored và sorted by rerank_score descending.
    """
    # TODO: Implement cross-encoder reranking
    #
    # Option A: Jina Reranker API
    # import requests
    # response = requests.post(
    #     "https://api.jina.ai/v1/rerank",
    #     headers={"Authorization": f"Bearer {JINA_API_KEY}"},
    #     json={
    #         "model": "jina-reranker-v2-base-multilingual",
    #         "query": query,
    #         "documents": [c["content"] for c in candidates],
    #         "top_n": top_k
    #     }
    # )
    # reranked = response.json()["results"]
    # return [
    #     {**candidates[r["index"]], "score": r["relevance_score"]}
    #     for r in reranked
    # ]
    #
    # Option B: Local model (Qwen3-Reranker)
    # from transformers import AutoModelForSequenceClassification, AutoTokenizer
    # ...
    raise NotImplementedError("Implement rerank_cross_encoder")


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance — chọn candidates vừa relevant vừa diverse.

    MMR = λ * sim(query, doc) - (1-λ) * max(sim(doc, selected_docs))

    Args:
        query_embedding: Vector embedding của query
        candidates: List of {'content': str, 'score': float, 'embedding': list, 'metadata': dict}
        top_k: Số lượng kết quả
        lambda_param: Trade-off giữa relevance (1.0) và diversity (0.0)

    Returns:
        List of top_k candidates selected by MMR.
    """
    # TODO: Implement MMR
    #
    # selected = []
    # remaining = list(range(len(candidates)))
    #
    # for _ in range(min(top_k, len(candidates))):
    #     best_idx = None
    #     best_score = float('-inf')
    #
    #     for idx in remaining:
    #         # Relevance to query
    #         relevance = cosine_sim(query_embedding, candidates[idx]["embedding"])
    #
    #         # Max similarity to already selected
    #         max_sim_to_selected = 0
    #         for sel_idx in selected:
    #             sim = cosine_sim(candidates[idx]["embedding"], candidates[sel_idx]["embedding"])
    #             max_sim_to_selected = max(max_sim_to_selected, sim)
    #
    #         # MMR score
    #         mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim_to_selected
    #
    #         if mmr_score > best_score:
    #             best_score = mmr_score
    #             best_idx = idx
    #
    #     selected.append(best_idx)
    #     remaining.remove(best_idx)
    #
    # return [candidates[i] for i in selected]
    raise NotImplementedError("Implement rerank_mmr")


def rerank_rrf(
    ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60
) -> list[dict]:
    """
    Reciprocal Rank Fusion — gộp kết quả từ nhiều ranker.

    RRF(d) = Σ 1 / (k + rank_r(d))

    Args:
        ranked_lists: List of ranked result lists (mỗi list từ 1 ranker)
        top_k: Số lượng kết quả cuối cùng
        k: Smoothing constant (default=60, từ paper Cormack et al. 2009)

    Returns:
        List of top_k candidates sorted by RRF score descending.
    """
    if not isinstance(ranked_lists, list):
        raise TypeError("ranked_lists must be a list of ranked result lists")
    if not isinstance(top_k, int) or not isinstance(k, int):
        raise TypeError("top_k and k must be integers")
    if top_k <= 0 or not ranked_lists:
        return []
    if k < 0:
        raise ValueError("k must be non-negative")

    def identity(item: dict[str, Any]) -> tuple[Any, ...]:
        """Ưu tiên ID chunk chung; fallback về content để merge dense/sparse."""

        metadata = item.get("metadata") or {}
        source = metadata.get("source")
        chunk_index = metadata.get("chunk_index")
        if source is not None and chunk_index is not None:
            return ("chunk", str(source), str(chunk_index))
        return ("content", str(item.get("content", "")))

    scores: dict[tuple[Any, ...], float] = {}
    representatives: dict[tuple[Any, ...], dict] = {}
    evidence: dict[tuple[Any, ...], list[dict[str, float | int]]] = {}
    first_seen: dict[tuple[Any, ...], int] = {}
    sequence = 0

    for list_index, ranked_list in enumerate(ranked_lists):
        if not isinstance(ranked_list, list):
            raise TypeError(f"ranked_lists[{list_index}] must be a list")

        seen_in_ranker: set[tuple[Any, ...]] = set()
        for rank, item in enumerate(ranked_list, start=1):
            if not isinstance(item, dict):
                raise TypeError(f"ranked_lists[{list_index}][{rank - 1}] must be a dict")
            if not isinstance(item.get("content"), str) or not item["content"].strip():
                raise ValueError("Every RRF candidate must have non-empty 'content'")
            if not isinstance(item.get("metadata", {}), dict):
                raise TypeError("Candidate 'metadata' must be a dict")

            key = identity(item)
            # Một ranker không được cộng điểm nhiều lần cho cùng chunk.
            if key in seen_in_ranker:
                continue
            seen_in_ranker.add(key)

            if key not in first_seen:
                first_seen[key] = sequence
                sequence += 1
                representatives[key] = {
                    **item,
                    "metadata": dict(item.get("metadata") or {}),
                }
            else:
                # Giữ metadata giàu nhất giữa dense và sparse.
                representatives[key]["metadata"] = {
                    **representatives[key].get("metadata", {}),
                    **item.get("metadata", {}),
                }

            contribution = 1.0 / (k + rank)
            scores[key] = scores.get(key, 0.0) + contribution
            evidence.setdefault(key, []).append(
                {
                    "list_index": list_index,
                    "rank": rank,
                    "original_score": float(item.get("score", 0.0)),
                }
            )

    ordered_keys = sorted(
        scores,
        key=lambda key: (-scores[key], first_seen[key]),
    )
    output: list[dict] = []
    for key in ordered_keys[:top_k]:
        item = representatives[key].copy()
        metadata = dict(item.get("metadata") or {})
        metadata["rrf_evidence"] = evidence[key]
        item["metadata"] = metadata
        item["score"] = round(scores[key], 8)
        output.append(item)
    return output


# =============================================================================
# Main rerank interface
# =============================================================================

def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "rrf",  # "cross_encoder" | "mmr" | "rrf"
) -> list[dict]:
    """
    Unified reranking interface.

    Args:
        query: Câu truy vấn
        candidates: Danh sách candidates từ retrieval
        top_k: Số lượng kết quả sau rerank
        method: Phương pháp reranking

    Returns:
        List of top_k reranked candidates.
    """
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    elif method == "mmr":
        # Cần query_embedding - embed query trước
        raise NotImplementedError("Call rerank_mmr with query_embedding")
    elif method == "rrf":
        # Với một list, RRF giữ nguyên thứ hạng nhưng chuẩn hóa score theo rank.
        return rerank_rrf([candidates], top_k=top_k)
    else:
        raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    dense = [
        {"content": "Atomic Habits: four laws", "score": 0.8, "metadata": {"source": "atomic.md", "chunk_index": 1}},
        {"content": "Deep Work", "score": 0.6, "metadata": {"source": "deep.md", "chunk_index": 0}},
    ]
    sparse = [
        {"content": "Atomic Habits: four laws", "score": 12.0, "metadata": {"source": "atomic.md", "chunk_index": 1}},
        {"content": "Thinking Fast and Slow", "score": 8.0, "metadata": {"source": "thinking.md", "chunk_index": 2}},
    ]
    results = rerank_rrf([dense, sparse], top_k=3)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content']}")
