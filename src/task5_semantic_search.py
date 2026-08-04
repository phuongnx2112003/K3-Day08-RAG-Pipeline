"""
Task 5 — Semantic Search Module.

Viết module tìm kiếm ngữ nghĩa (dense retrieval) trên vector store.

Yêu cầu:
    - Input: query string + top_k
    - Output: danh sách chunks có score, sorted descending
    - Phải tương thích với embedding model và vector store ở Task 4
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from .task4_chunking_indexing import get_collection, get_jina_embeddings
except ImportError:
    from task4_chunking_indexing import get_collection, get_jina_embeddings


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector similarity với Jina Embeddings API.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,      # Nội dung chunk
            'score': float,      # Cosine similarity score
            'metadata': dict     # source, doc_type, chunk_index
        }
        Sorted by score descending.
    """
    if not query.strip():
        return []

    collection = get_collection()

    if collection.count() == 0:
        return []

    query_vector = get_jina_embeddings([query], is_query=True)[0]

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    if results and results.get("documents") and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            # ChromaDB cosine distance d in [0, 2].
            # Cosine similarity = 1 - distance.
            score = max(0.0, 1.0 - dist)
            output.append({
                "content": doc,
                "score": round(score, 4),
                "metadata": meta
            })

    output.sort(key=lambda x: x["score"], reverse=True)
    return output[:top_k]


if __name__ == "__main__":
    query = "Phương pháp 4 bước để xây dựng thói quen tốt theo Atomic Habits"
    print(f"Searching for: '{query}'\n")
    results = semantic_search(query, top_k=5)
    for r in results:
        print(f"[{r['score']:.4f}] [{r['metadata'].get('source')}] {r['content'][:100]}...\n")
