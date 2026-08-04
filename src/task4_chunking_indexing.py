"""
Task 4 — Chunking & Indexing vào Vector Store.

Hướng dẫn:
    1. Đọc toàn bộ markdown files từ data/standardized/
    2. Chọn 1 chunking strategy (giải thích lý do)
    3. Chọn 1 embedding model (giải thích lý do)
    4. Index vào vector store (ChromaDB)
"""

import os
import re
from pathlib import Path
import requests
try:  # Keep the data-preparation functions usable before optional deps are installed.
    import chromadb
except ImportError:  # pragma: no cover - exercised in minimal environments
    chromadb = None
from dotenv import load_dotenv
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover - simple compatible fallback below
    RecursiveCharacterTextSplitter = None

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# =============================================================================
# CONFIGURATION
# =============================================================================

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
CHUNKING_METHOD = "recursive"

# Sử dụng Jina Embeddings API v3 cho kết quả rất chính xác và không tốn bộ nhớ local
EMBEDDING_MODEL = os.getenv("JINA_EMBEDDING_MODEL", "jina-embeddings-v3")
EMBEDDING_DIM = int(os.getenv("JINA_EMBEDDING_DIM", "1024"))
JINA_EMBEDDING_URL = os.getenv("JINA_EMBEDDING_BASE_URL", "https://api.jina.ai/v1/embeddings")

VECTOR_STORE = "chromadb"
COLLECTION_NAME = "university_services_docs"

_collection = None


def get_jina_embeddings(texts: list[str], is_query: bool = False) -> list[list[float]]:
    """
    Gọi Jina Embeddings API để lấy vector representations.
    """
    if not texts:
        return []

    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        raise ValueError("Thiếu JINA_API_KEY trong file .env!")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    task_type = "retrieval.query" if is_query else "retrieval.passage"
    all_embeddings = []
    batch_size = 32

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        payload = {
            "model": EMBEDDING_MODEL,
            "task": task_type,
            "dimensions": EMBEDDING_DIM,
            "embedding_type": "float",
            "input": batch
        }
        response = requests.post(JINA_EMBEDDING_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        all_embeddings.extend([item["embedding"] for item in sorted_data])

    return all_embeddings


def get_collection():
    global _collection
    if chromadb is None:
        raise RuntimeError("ChromaDB is not installed. Run: pip install -r requirements.txt")
    if _collection is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def load_documents() -> list[dict]:
    """
    Đọc toàn bộ markdown files từ data/standardized/.
    """
    documents = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        if md_file.name.startswith("."):
            continue
        content = md_file.read_text(encoding="utf-8")
        doc_type = "legal" if "legal" in str(md_file.parent) else "news"
        def field(name: str) -> str:
            match = re.search(rf"^\*\*{name}:\*\*\s*(.+)$", content, re.MULTILINE)
            return match.group(1).strip() if match else ""
        title = next((line[2:].strip() for line in content.splitlines() if line.startswith("# ")), md_file.stem)
        documents.append({
            "content": content,
            "metadata": {
                "source": md_file.name,
                "type": field("Type") or doc_type,
                "book_title": field("Book") or title,
                "author": field("Author"),
                "category": field("Category"),
                "source_url": field("Source"),
                "rights_note": "public-source-or-team-summary",
            }
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Chunk documents theo RecursiveCharacterTextSplitter.
    """
    chunks = []
    for doc in documents:
        if RecursiveCharacterTextSplitter is None:
            # Dependency-free fallback preserving the same size/overlap contract.
            text = doc["content"]
            step = CHUNK_SIZE - CHUNK_OVERLAP
            splits = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), step)]
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
            splits = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(splits):
            chunk_metadata = {**doc["metadata"], "chunk_index": i}
            chunks.append({
                "content": chunk_text,
                "metadata": chunk_metadata
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed toàn bộ chunks bằng Jina API.
    """
    if not chunks:
        return []

    texts = [c["content"] for c in chunks]
    print(f"Calling Jina API to embed {len(texts)} chunks...")
    embeddings = get_jina_embeddings(texts, is_query=False)

    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb
    return chunks


def index_to_vectorstore(chunks: list[dict]):
    """
    Lưu chunks vào vector store ChromaDB.
    """
    if not chunks:
        print("No chunks to index.")
        return

    collection = get_collection()

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for i, c in enumerate(chunks):
        source = c["metadata"].get("source", "doc")
        chunk_idx = c["metadata"].get("chunk_index", i)
        doc_id = f"{source}_chunk_{chunk_idx}_{i}"

        ids.append(doc_id)
        documents.append(c["content"])
        embeddings.append(c["embedding"])
        metadatas.append(c["metadata"])

    # Reset/Clear old data before upsert if collection already has documents
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )


def run_pipeline():
    """Chạy toàn bộ pipeline: load → chunk → embed → index."""
    print("=" * 50)
    print("Task 4: Chunking & Indexing (via Jina API)")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: {VECTOR_STORE}")
    print("=" * 50)

    docs = load_documents()
    print(f"\n✓ Loaded {len(docs)} documents")

    chunks = chunk_documents(docs)
    print(f"✓ Created {len(chunks)} chunks")

    chunks = embed_chunks(chunks)
    print(f"✓ Embedded {len(chunks)} chunks via Jina API")

    index_to_vectorstore(chunks)
    print("✓ Indexed to ChromaDB vector store")


if __name__ == "__main__":
    run_pipeline()
