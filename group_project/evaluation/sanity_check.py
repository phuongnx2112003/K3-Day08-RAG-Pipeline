"""
Sanity Check Script cho Role 6 (Minh Đức) - CP2 Evaluation.

Script này sẽ:
1. Tự động kiểm tra và build ChromaDB vector store (Task 4) nếu chưa có.
2. Lấy 5 câu Sanity Check đại diện từ golden_dataset.json.
3. Chạy qua Semantic Search (Role 3) & Lexical Search BM25 (Role 4).
4. So sánh kết quả retrieval, score và source document.
"""

import sys
import json
from pathlib import Path

# Cấu hình UTF-8 cho Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm đường dẫn root dự án vào sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.task4_chunking_indexing import run_pipeline as build_chroma_db, CHROMA_DIR
from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search


def run_sanity_check():
    print("=" * 70)
    print("🚀 ROLE 6: BẮT ĐẦU CHẠY EVALUATION SANITY CHECK (CP2)")
    print("=" * 70)

    # Step 1: Kiểm tra và Index ChromaDB nếu cần
    if not CHROMA_DIR.exists() or not any(CHROMA_DIR.iterdir()):
        print("\n📦 ChromaDB chưa tồn tại. Đang tiến hành Chunking & Indexing (Task 4)...")
        build_chroma_db()
    else:
        print("\n✅ ChromaDB đã sẵn sàng.")

    # Step 2: Load Golden Dataset
    golden_path = Path(__file__).parent / "golden_dataset.json"
    with open(golden_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # Chọn 5 câu đại diện cho 5 loại
    target_ids = ["Q01", "Q02", "Q03", "Q11", "Q18"]
    test_cases = [item for item in dataset if item.get("id") in target_ids]

    if not test_cases:
        test_cases = dataset[:5]

    print(f"\n📋 Đã chọn {len(test_cases)} câu hỏi Sanity Check tiêu biểu:")
    for idx, item in enumerate(test_cases, 1):
        print(f"  {idx}. [{item.get('category')}] {item['question']}")

    print("\n" + "=" * 70)

    # Step 3: Đánh giá từng câu
    for idx, item in enumerate(test_cases, 1):
        q_id = item.get("id", f"Q{idx}")
        category = item.get("category", "General")
        query = item["question"]
        expected_context = item.get("expected_context", "N/A")

        print(f"\n🔍 [{q_id}] ({category}): \"{query}\"")
        print(f"📌 Expected Context: {expected_context}")

        # 3a. Dense Search (Role 3)
        print("\n  🔹 [Role 3] Dense / Semantic Search (ChromaDB + Jina API):")
        try:
            dense_res = semantic_search(query, top_k=2)
            if not dense_res:
                print("     ❌ Không tìm thấy kết quả nào.")
            for r_idx, r in enumerate(dense_res, 1):
                source = r["metadata"].get("source", "unknown")
                score = r["score"]
                snippet = r["content"][:110].replace("\n", " ")
                print(f"     {r_idx}. Score: {score:.4f} | Source: {source} | Snippet: {snippet}...")
        except Exception as e:
            print(f"     ⚠️ Lỗi Dense Search: {e}")

        # 3b. Lexical Search (Role 4)
        print("\n  🔸 [Role 4] Lexical Search (BM25):")
        try:
            lexical_res = lexical_search(query, top_k=2)
            if not lexical_res:
                print("     ❌ Không tìm thấy kết quả nào.")
            for r_idx, r in enumerate(lexical_res, 1):
                source = r["metadata"].get("source", "unknown")
                score = r["score"]
                snippet = r["content"][:110].replace("\n", " ")
                print(f"     {r_idx}. Score: {score:.4f} | Source: {source} | Snippet: {snippet}...")
        except Exception as e:
            print(f"     ⚠️ Lỗi Lexical Search: {e}")

        print("-" * 70)

    print("\n🎉 HOÀN THÀNH CP2 SANITY CHECK FOR ROLE 6!")


if __name__ == "__main__":
    run_sanity_check()
