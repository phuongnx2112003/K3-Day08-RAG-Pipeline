# Kịch Bản Demo - Role 1

**Người điều phối:** Nguyễn Xuân Phượng - Team Leader & RAG Architect

## Kiến Trúc Trình Bày

```text
Nguồn PDF + bài viết
        |
        v
Role 2: Crawl, lưu metadata, convert Markdown
        |
        v
Role 3: Chunking + ChromaDB + Dense Search/HyDE
        |                              |
        |                              v
        |                     Role 4: BM25 + RRF + PageIndex
        |                              |
        +------------------------------+
                                       v
                         Task 9: Hybrid Retrieval Pipeline
                                       |
                                       v
                         Role 5: Task 10 + Streamlit UI
                                       |
                                       v
                         Role 6: Golden dataset + RAGAS
```

`src/supervisor.py` là lớp điều phối của Role 1. Lớp này không thay thế các module của thành viên khác; nó cung cấp một giao diện chung cho UI, demo và evaluation:

```text
PipelineSupervisor.answer(query) -> Task 10 -> Task 9 -> Dense + BM25 + RRF + PageIndex
PipelineSupervisor.retrieve_evidence(query) -> Task 9 -> evidence chunks
```

## Điều Kiện Bàn Giao Giữa Các Role

| Từ | Sang | Bàn giao bắt buộc |
|---|---|---|
| Role 2 | Role 3, Role 4 | Markdown tại `data/standardized/`, metadata có `source` và `type` |
| Role 3 | Role 4, Role 1 | `semantic_search()` trả `content`, `score`, `metadata`; score là cosine gốc |
| Role 4 | Role 1 | `lexical_search()`, `rerank_rrf()`, `pageindex_search()` trả cùng format chunk |
| Role 1 | Role 5, Role 6 | `PipelineSupervisor.answer()` trả `answer`, `sources`, `retrieval_source` |
| Role 5 | Role 6 | Câu trả lời hiển thị citation và nguồn đã dùng |

## Chuẩn Bị Trước Demo

1. Role 2 xác nhận có tối thiểu 3 tài liệu chính sách, 5 bài tin và Markdown đã chuẩn hóa.
2. Role 3 chạy index và kiểm tra semantic search trả về kết quả đã sắp theo score giảm dần.
3. Role 4 kiểm tra RRF; fallback phải dùng cosine gốc của dense search, không dùng điểm RRF.
4. Phượng chạy `python3 -m src.supervisor`; cả Task 9 và Task 10 phải hiện `READY`. Trạng thái `BLOCKED` sẽ chỉ rõ worker nào vẫn là template hoặc không import được.
5. Role 5 chạy `streamlit run app.py`; Role 6 chuẩn bị kết quả RAGAS và 20 câu hỏi golden dataset.

## Luồng Demo Gợi Ý

1. Phượng giới thiệu mục tiêu và sơ đồ kiến trúc trong khoảng 1 phút.
2. Role 2 trình bày nguồn dữ liệu và một file Markdown đã chuẩn hóa.
3. Role 3/4 nhập một câu hỏi có từ khóa rõ ràng để minh họa Dense + BM25 + RRF.
4. Role 5 chạy chatbot, chỉ ra citation và source documents.
5. Nhập một câu hỏi ngoài phạm vi hoặc tổng hợp để minh họa fallback; giải thích ngưỡng dùng cosine gốc.
6. Role 6 trình bày bảng benchmark, cấu hình A/B và các trường hợp cần cải thiện.

## Phương Án Dự Phòng

| Rủi ro | Cách xử lý khi demo |
|---|---|
| API PageIndex hoặc LLM không phản hồi | Chuyển sang câu hỏi đã chuẩn bị dùng hybrid retrieval; trình bày log/kết quả benchmark đã lưu. |
| Chưa có API key | Dùng test Supervisor và màn hình UI với thông báo lỗi rõ ràng, không khẳng định là đã sinh câu trả lời. |
| Kết quả retrieval kém | Kiểm tra metadata, chạy lại index sau khi làm sạch `chroma_db/`, sau đó hạ số câu hỏi demo xuống các câu đã có evidence. |
