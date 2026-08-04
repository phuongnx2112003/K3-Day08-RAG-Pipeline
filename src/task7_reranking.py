"""Task 7 — Jina cloud reranking with deterministic local fallbacks."""

from __future__ import annotations

import os
import re
from collections import Counter

import requests

JINA_RERANK_URL = os.getenv("JINA_RERANK_BASE_URL", "https://api.jina.ai/v1/rerank")
JINA_RERANK_MODEL = os.getenv("JINA_RERANK_MODEL", "jina-reranker-v2-base-multilingual")


def _overlap_score(query: str, content: str) -> float:
    query_terms = set(re.findall(r"[^\W_]+", query.lower()))
    content_terms = set(re.findall(r"[^\W_]+", content.lower()))
    return len(query_terms & content_terms) / max(len(query_terms), 1)


def rerank_cross_encoder(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """Use Jina Reranker when configured; otherwise make a transparent local rerank."""
    if not candidates or top_k <= 0:
        return []
    api_key = os.getenv("JINA_API_KEY")
    if api_key:
        try:
            response = requests.post(
                JINA_RERANK_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": JINA_RERANK_MODEL, "query": query,
                      "documents": [item.get("content", "") for item in candidates], "top_n": top_k},
                timeout=30,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            ranked = []
            for result in results:
                index = result.get("index")
                if isinstance(index, int) and 0 <= index < len(candidates):
                    ranked.append({**candidates[index], "score": float(result.get("relevance_score", 0.0))})
            if ranked:
                return ranked[:top_k]
        except (requests.RequestException, ValueError, TypeError):
            pass
    ranked = [
        {**item, "score": 0.7 * _overlap_score(query, item.get("content", "")) + 0.3 * float(item.get("score", 0.0))}
        for item in candidates
    ]
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:top_k]


def rerank_rrf(ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60) -> list[dict]:
    """Fuse rank lists. Scores are fusion scores, not relevance thresholds."""
    fused: dict[str, float] = {}
    records: dict[str, dict] = {}
    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, start=1):
            key = item.get("content", "")
            if not key:
                continue
            fused[key] = fused.get(key, 0.0) + 1 / (k + rank)
            records.setdefault(key, item)
    return [{**records[key], "score": score} for key, score in sorted(fused.items(), key=lambda item: item[1], reverse=True)[:top_k]]


def rerank(query: str, candidates: list[dict], top_k: int = 5, method: str = "cross_encoder") -> list[dict]:
    """Public reranking contract. RRF fusion belongs in :func:`rerank_rrf`."""
    if method in {"cross_encoder", "rrf"}:
        return rerank_cross_encoder(query, candidates, top_k)
    if method == "none":
        return list(candidates)[:top_k]
    raise ValueError(f"Unknown reranking method: {method}")
