"""Task 6 — Sparse retrieval bằng BM25 và TF-IDF.

Module ưu tiên dùng đúng chunks đã được Task 4 ghi vào ChromaDB. Khi vector store
chưa tồn tại, module dùng ``load_documents()/chunk_documents()`` của Task 4; trong
giai đoạn hai hàm đó chưa hoàn thiện, một fallback cục bộ với cùng cấu hình 800/100
giúp BM25 vẫn có thể được phát triển và kiểm thử độc lập.

Contract kết quả thống nhất với dense retrieval::

    {"content": str, "score": float, "metadata": dict}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Sequence

from rank_bm25 import BM25Okapi

from .text_normalization import tokenize_bm25


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STANDARDIZED_DIR = PROJECT_ROOT / "data" / "standardized"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "university_services_docs"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

SearchMethod = Literal["bm25", "tfidf"]
CorpusItem = dict[str, Any]

# Public để các task khác có thể dùng chung/kiểm tra corpus đã nạp.
CORPUS: list[CorpusItem] = []

_BM25_INDEX: BM25Okapi | None = None
_TFIDF_VECTORIZER: Any | None = None
_TFIDF_MATRIX: Any | None = None


def _validate_corpus(corpus: Sequence[CorpusItem]) -> list[CorpusItem]:
    """Kiểm tra và copy nông corpus để index không làm đổi dữ liệu đầu vào."""

    validated: list[CorpusItem] = []
    for index, item in enumerate(corpus):
        if not isinstance(item, dict):
            raise TypeError(f"corpus[{index}] must be a dict")

        content = item.get("content")
        metadata = item.get("metadata", {})
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"corpus[{index}]['content'] must be a non-empty string")
        if not isinstance(metadata, dict):
            raise TypeError(f"corpus[{index}]['metadata'] must be a dict")

        validated.append({"content": content, "metadata": dict(metadata)})

    if not validated:
        raise ValueError("corpus must contain at least one document/chunk")
    return validated


def build_bm25_index(corpus: Sequence[CorpusItem]) -> BM25Okapi:
    """Xây BM25Okapi từ corpus bằng tokenizer Unicode dùng chung cho query."""

    validated = _validate_corpus(corpus)
    tokenized_corpus = [tokenize_bm25(item["content"]) for item in validated]
    if any(not tokens for tokens in tokenized_corpus):
        raise ValueError("Every corpus item must contain at least one searchable token")
    return BM25Okapi(tokenized_corpus, k1=1.5, b=0.75)


def build_tfidf_index(corpus: Sequence[CorpusItem]):
    """Xây TF-IDF L2-normalized; tích vô hướng sau đó chính là cosine score."""

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError as exc:  # pragma: no cover - phụ thuộc môi trường cài đặt
        raise RuntimeError(
            "TF-IDF requires scikit-learn. Run: pip install scikit-learn"
        ) from exc

    validated = _validate_corpus(corpus)
    vectorizer = TfidfVectorizer(
        tokenizer=tokenize_bm25,
        preprocessor=None,
        token_pattern=None,
        lowercase=False,
        norm="l2",
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(item["content"] for item in validated)
    return vectorizer, matrix


def _load_markdown_fallback() -> list[CorpusItem]:
    """Mirror chính xác loader và RecursiveCharacterTextSplitter của Task 4."""

    if not STANDARDIZED_DIR.exists():
        raise FileNotFoundError(f"Corpus directory does not exist: {STANDARDIZED_DIR}")

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as exc:  # pragma: no cover - dependency nằm trong requirements.txt
        raise RuntimeError(
            "Task 6 requires langchain-text-splitters to mirror Task 4 chunks"
        ) from exc

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: list[CorpusItem] = []
    for path in STANDARDIZED_DIR.rglob("*.md"):
        if path.name.startswith("."):
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        doc_type = "legal" if "legal" in str(path.parent) else "news"
        for chunk_index, content in enumerate(splitter.split_text(text)):
            chunks.append(
                {
                    "content": content,
                    "metadata": {
                        "source": path.name,
                        "type": doc_type,
                        "chunk_index": chunk_index,
                    },
                }
            )
    return chunks


def _load_from_chroma() -> list[CorpusItem]:
    """Đọc đúng chunks của dense index nếu ChromaDB đã được Role 3 tạo."""

    if not CHROMA_DIR.exists():
        return []
    try:
        from .task4_chunking_indexing import get_collection

        collection = get_collection()
        if collection.count() == 0:
            return []
        payload = collection.get(include=["documents", "metadatas"])
    except (ImportError, ValueError, KeyError, RuntimeError):
        return []

    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or [{} for _ in documents]
    return [
        {"content": content, "metadata": dict(metadata or {})}
        for content, metadata in zip(documents, metadatas)
        if isinstance(content, str) and content.strip()
    ]


def _load_from_task4() -> list[CorpusItem]:
    """Dùng trực tiếp loader/chunker Task 4 khi hai hàm đã được hoàn thiện."""

    try:
        from .task4_chunking_indexing import chunk_documents, load_documents

        return chunk_documents(load_documents())
    except (ImportError, NotImplementedError, FileNotFoundError):
        return []


def load_shared_corpus() -> list[CorpusItem]:
    """Nạp corpus theo ưu tiên Chroma → Task 4 → Markdown fallback."""

    corpus = _load_from_chroma() or _load_from_task4() or _load_markdown_fallback()
    return _validate_corpus(corpus)


def initialize_indexes(
    corpus: Sequence[CorpusItem] | None = None,
    *,
    include_tfidf: bool = False,
) -> int:
    """Nạp corpus và tạo index; trả số chunks đã index."""

    global CORPUS, _BM25_INDEX, _TFIDF_VECTORIZER, _TFIDF_MATRIX

    CORPUS = _validate_corpus(corpus if corpus is not None else load_shared_corpus())
    _BM25_INDEX = build_bm25_index(CORPUS)
    _TFIDF_VECTORIZER = None
    _TFIDF_MATRIX = None
    if include_tfidf:
        _TFIDF_VECTORIZER, _TFIDF_MATRIX = build_tfidf_index(CORPUS)
    return len(CORPUS)


def _ensure_index(method: SearchMethod) -> None:
    global _TFIDF_VECTORIZER, _TFIDF_MATRIX

    if not CORPUS:
        initialize_indexes(include_tfidf=method == "tfidf")
    elif _BM25_INDEX is None:
        initialize_indexes(CORPUS, include_tfidf=method == "tfidf")
    elif method == "tfidf" and _TFIDF_VECTORIZER is None:
        _TFIDF_VECTORIZER, _TFIDF_MATRIX = build_tfidf_index(CORPUS)


def _rank_results(scores: Sequence[float], top_k: int) -> list[CorpusItem]:
    ranked_indices = sorted(
        range(len(scores)),
        key=lambda index: (-float(scores[index]), index),
    )
    results: list[CorpusItem] = []
    for index in ranked_indices:
        score = round(float(scores[index]), 4)
        if score <= 0:
            continue
        results.append(
            {
                "content": CORPUS[index]["content"],
                "score": score,
                "metadata": dict(CORPUS[index]["metadata"]),
            }
        )
        if len(results) >= top_k:
            break
    return results


def lexical_search(
    query: str,
    top_k: int = 10,
    method: SearchMethod = "bm25",
) -> list[CorpusItem]:
    """Tìm kiếm sparse và trả chunks theo score giảm dần.

    Args:
        query: Câu truy vấn Unicode.
        top_k: Số kết quả dương tối đa.
        method: ``"bm25"`` (mặc định) hoặc ``"tfidf"``.
    """

    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not isinstance(top_k, int):
        raise TypeError("top_k must be an integer")
    if top_k <= 0 or not query.strip():
        return []
    if method not in ("bm25", "tfidf"):
        raise ValueError("method must be 'bm25' or 'tfidf'")

    query_tokens = tokenize_bm25(query)
    if not query_tokens:
        return []
    _ensure_index(method)

    if method == "bm25":
        assert _BM25_INDEX is not None
        scores = _BM25_INDEX.get_scores(query_tokens)
    else:
        assert _TFIDF_VECTORIZER is not None and _TFIDF_MATRIX is not None
        query_vector = _TFIDF_VECTORIZER.transform([query])
        scores = (_TFIDF_MATRIX @ query_vector.T).toarray().ravel()

    return _rank_results(scores, min(top_k, len(CORPUS)))


if __name__ == "__main__":
    count = initialize_indexes(include_tfidf=True)
    print(f"Indexed {count} chunks")
    for search_method in ("bm25", "tfidf"):
        print(f"\n{search_method.upper()}")
        for result in lexical_search(
            "four laws of behavior change Atomic Habits",
            top_k=3,
            method=search_method,
        ):
            source = result["metadata"].get("source", "unknown")
            print(f"[{result['score']:.4f}] {source}: {result['content'][:100]}...")
