# Checkpoint 3 — Role 4: RRF và PageIndex Fallback

## Task 7 — Reciprocal Rank Fusion

- Công thức: `RRF(d) = Σ 1 / (k + rank_r(d))`, mặc định `k=60`.
- Chunk được nhận diện bằng `metadata.source + metadata.chunk_index`; fallback bằng content.
- Một chunk trùng trong cùng ranker chỉ được cộng điểm một lần.
- Giữ lại score/rank gốc trong `metadata.rrf_evidence` để debug.
- Không dùng RRF score để quyết định fallback.

Kết quả smoke test: chunk Atomic Habits đứng top 1 vì xuất hiện hạng 1 ở cả dense và
BM25, score `2 / 61 = 0.03278689`.

## Task 8 — PageIndex

- SDK: `pageindex==0.2.8`.
- Corpus 9 Markdown được ghép thành `pageindex_pdfs/book_review_corpus.pdf`.
- PDF local: khoảng 166 KB, có heading `DOCUMENT` và `SOURCE_FILE` để truy vết.
- Registry ID: `pageindex_doc_ids.json` (không commit key hoặc ID runtime).
- Output: `content`, `score`, `metadata`, `source="pageindex"`.
- Parser hỗ trợ schema `retrieved_nodes -> relevant_contents` lồng nhiều cấp.
- Khi API/key/document chưa sẵn sàng, fallback trả `[]` thay vì làm crash pipeline;
  dùng `strict=True` khi debug để nhận exception đầy đủ.
- PDF tổng hợp đã upload thành công và trạng thái PageIndex là `ready`.
- Query thật về Four Laws trả 5 đoạn, đúng section Atomic Habits và bốn quy luật.
- Query ngoài domain về giá Bitcoin trả 0 đoạn (`[]`), không tạo evidence giả.

## Hiệu chỉnh fallback bằng cosine gốc

| Nhóm | Query | Top cosine |
|---|---|---:|
| In-domain | Four laws — Atomic Habits | 0.7050 |
| In-domain | System 1/System 2 — Thinking Fast and Slow | 0.7264 |
| In-domain | Validated learning — Lean Startup | 0.6255 |
| Out-domain | Weather in Ho Chi Minh City | 0.0756 |
| Out-domain | How to cook Vietnamese pho | 0.1569 |
| Out-domain | Current Bitcoin price | 0.1804 |
| Out-domain | Winner of 2022 FIFA World Cup | 0.1630 |

Khoảng cách quan sát được: out-domain tối đa `0.1804`, in-domain tối thiểu `0.6255`.
Ngưỡng khuyến nghị ban đầu là `0.4`, nằm giữa hai nhóm. Task 9 phải dùng top cosine
gốc từ Task 5 để so với ngưỡng này, tuyệt đối không dùng RRF score.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_task7_task8 -v
```

Các unit test bao phủ: fusion nhiều ranker, chống duplicate, output order, parse response
PageIndex, thiếu registry không gọi mạng, và fallback dựa trên dense score.

Smoke test tích hợp thật:

- Dense top-1: `atomic-habits-business-appendix.md`, cosine `0.7052`.
- BM25 top-1: cùng tài liệu, chunk 39, score `22.8969`.
- RRF top-1: chunk 0 của cùng tài liệu, nhận evidence từ dense rank 1 và BM25 rank 4,
  fused score `0.03201844`.
