"""Task 6 — BM25 lexical retrieval over the same chunks as dense retrieval."""

from __future__ import annotations

import math
import re
from collections import Counter

try:
    from rank_bm25 import BM25Okapi
except ImportError:  # A small standards-compatible fallback for first-run demos.
    BM25Okapi = None

from .task4_chunking_indexing import chunk_documents, load_documents

CORPUS: list[dict] = []
_bm25 = None
_corpus_signature: tuple[tuple[str, int], ...] | None = None


def _tokenize(text: str) -> list[str]:
    """Unicode-friendly tokenisation for both Vietnamese and English queries."""
    return re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE)


def build_bm25_index(corpus: list[dict]):
    """Build a BM25Okapi index; returns a portable fallback when unavailable."""
    tokenized = [_tokenize(doc.get("content", "")) for doc in corpus]
    return BM25Okapi(tokenized) if BM25Okapi is not None and tokenized else tokenized


def _fallback_scores(query_tokens: list[str], tokenized_corpus: list[list[str]]) -> list[float]:
    """BM25 implementation used only if rank-bm25 has not been installed yet."""
    if not tokenized_corpus or not query_tokens:
        return [0.0] * len(tokenized_corpus)
    total_docs = len(tokenized_corpus)
    avg_len = sum(len(doc) for doc in tokenized_corpus) / total_docs or 1.0
    doc_freq = Counter(token for doc in tokenized_corpus for token in set(doc))
    k1, b = 1.5, 0.75
    scores = []
    for doc in tokenized_corpus:
        frequencies = Counter(doc)
        score = 0.0
        for token in query_tokens:
            if not frequencies[token]:
                continue
            idf = math.log(1 + (total_docs - doc_freq[token] + 0.5) / (doc_freq[token] + 0.5))
            denom = frequencies[token] + k1 * (1 - b + b * len(doc) / avg_len)
            score += idf * frequencies[token] * (k1 + 1) / denom
        scores.append(score)
    return scores


def _get_index() -> tuple[list[dict], object]:
    global CORPUS, _bm25, _corpus_signature
    documents = load_documents()
    corpus = chunk_documents(documents)
    signature = tuple((item["metadata"].get("source", ""), item["metadata"].get("chunk_index", 0)) for item in corpus)
    if signature != _corpus_signature:
        CORPUS, _bm25, _corpus_signature = corpus, build_bm25_index(corpus), signature
    return CORPUS, _bm25


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Return non-zero BM25 matches, descending by score, with chunk metadata."""
    if not query or not query.strip() or top_k <= 0:
        return []
    corpus, index = _get_index()
    if not corpus:
        return []
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    scores = index.get_scores(query_tokens) if BM25Okapi is not None else _fallback_scores(query_tokens, index)
    ranked = sorted(enumerate(scores), key=lambda item: float(item[1]), reverse=True)
    return [
        {"content": corpus[i]["content"], "score": float(score), "metadata": corpus[i]["metadata"].copy()}
        for i, score in ranked[:top_k]
        if float(score) > 0
    ]
