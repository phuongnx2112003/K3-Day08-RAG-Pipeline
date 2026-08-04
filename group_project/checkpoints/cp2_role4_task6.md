# Checkpoint 2 — Role 4: Task 6 BM25/TF-IDF

## Kết quả triển khai

- Nguồn corpus: ưu tiên chunks trong ChromaDB, sau đó Task 4, cuối cùng Markdown fallback.
- Cấu hình fallback: `CHUNK_SIZE=800`, `CHUNK_OVERLAP=100`.
- Số chunks hiện tại: 229, bằng đúng output Task 4.
- BM25: `rank-bm25` với `k1=1.5`, `b=0.75`.
- TF-IDF: unigram Unicode, sublinear TF và cosine similarity.
- Tokenizer: Unicode NFKC, casefold, giữ dấu tiếng Việt, số và từ ghép.
- Output contract: `content`, `score`, `metadata`; score làm tròn 4 chữ số như Task 5.

## Kiểm thử truy vấn

Query: `four laws of behavior change Atomic Habits`

- BM25 top-1: `article_01.md` — bài tóm tắt Atomic Habits chính thức.
- TF-IDF top-1: chunk chứa trực tiếp danh sách `Laws of Behavior Change`.
- Kết quả được sắp xếp score giảm dần và loại các kết quả có score bằng 0.

## Đối chiếu Task 4–5

- Task 4 chunks: 229.
- Task 6 chunks: 229.
- So sánh toàn bộ `content` và `metadata`: exact equality.
- Metadata chung: `source`, `type`, `chunk_index`.
- Task 5 và Task 6 cùng trả `content`, `score`, `metadata` và score 4 chữ số.
- ChromaDB local đã được tạo với đúng 229 records bằng `jina-embeddings-v3`.
- Dense retrieval đã chạy thật; top score cho query Atomic Habits là `0.6715`.
- BM25 đọc lại collection và trả `article_01.md` ở top 1 với score `16.1345`.

## Lệnh chạy

```powershell
.\.venv\Scripts\python.exe -m src.task6_lexical_search
.\.venv\Scripts\python.exe -m unittest tests.test_task6_lexical_search -v
```

## Ghi chú tích hợp

`lexical_search(query, top_k, method="bm25")` là interface mặc định cho Task 9.
Dùng `method="tfidf"` khi cần benchmark. Khi Role 3 đã tạo Chroma collection
`university_services_docs`, sparse retrieval sẽ đọc lại đúng documents và metadata
từ collection để RRF có thể nhận diện cùng chunk giữa dense và sparse. Khi collection
chưa được tạo, Task 6 gọi trực tiếp `load_documents()` và `chunk_documents()` của
Task 4; fallback cuối cũng mirror chính xác schema `source`, `type`, `chunk_index`.
