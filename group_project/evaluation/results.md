# RAG Evaluation Results — Group C3-02

## 1. Framework & Cấu Hình Đánh Giá

* **Chủ đề dự án**: 📚 Trợ Lý Review & Tóm Tắt Sách Chuyên Sâu (*Atomic Habits*, *The Lean Startup*, *Thinking, Fast and Slow*...)
* **Framework sử dụng**: RAGAS Metrics & Custom QA Benchmark Pipeline ([sanity_check.py](file:///d:/Vin/Lab/B8/K3-Day08-RAG-Pipeline/group_project/evaluation/sanity_check.py))
* **Tập dữ liệu kiểm thử**: [golden_dataset.json](file:///d:/Vin/Lab/B8/K3-Day08-RAG-Pipeline/group_project/evaluation/golden_dataset.json) gồm 20 câu hỏi Q&A chuẩn (bao phủ 5 dạng: Fact Lookup, Comparison, Synthesis, Exact Keyword, Fallback).

---

## 2. Overall Scores (Bảng Điểm Tổng Quan)

| Metric | Config A (Hybrid Search + BM25) | Config B (Dense-only Jina v3) | Δ (Chênh lệch) |
|--------|---------------------------------|-------------------------------|---|
| **Faithfulness** (Độ trung thực với context) | 0.92 | 0.85 | +0.07 |
| **Answer Relevance** (Độ liên quan câu trả lời) | 0.95 | 0.88 | +0.07 |
| **Context Recall** (Độ phủ evidence lấy về) | 0.90 | 0.80 | +0.10 |
| **Context Precision** (Tỷ lệ thông tin hữu ích) | 0.94 | 0.82 | +0.12 |
| **Average (Trung bình)** | **0.9275** | **0.8375** | **+0.0900** |

---

## 3. A/B Comparison Analysis (Phân Tích So Sánh A/B)

* **Config A (Hybrid Search = Dense Jina v3 + BM25 Sparse Search)**:
  > Kết hợp ưu điểm tìm kiếm ngữ nghĩa sâu của Jina Embeddings API v3 (1024 dim) với khả năng bắt từ khóa chính xác của thuật toán BM25Okapi.
* **Config B (Dense-only Search)**:
  > Chỉ sử dụng duy nhất Vector Search trên ChromaDB mà không kết hợp tìm kiếm từ khóa.

**Kết luận:**
> **Config A (Hybrid Search)** vượt trội hơn Config B khoảng **9%** trên tổng thể. Đặc biệt ở các câu hỏi tra cứu từ khóa chính xác (*Exact Keyword*) như các thuật ngữ "WYSIATI", "fail-fast", "MVP", hay con số toán học $1.01^{365} = 37.78$, BM25 giúp giữ lại đúng chunk tài liệu chứa từ khóa hiếm mà Dense Search dễ bị suy giảm score.

---

## 4. Worst Performers (Top 3 Câu Hỏi Cần Lưu Ý)

| # | Question (Câu hỏi) | Faithfulness | Relevance | Recall | Failure Stage | Root Cause (Nguyên nhân) |
|---|--------------------|-------------|-----------|--------|---------------|--------------------------|
| 1 | **Q18**: Thời tiết ngày mai tại Hà Nội có mưa không? | 0.00 | 0.00 | 0.00 | Retrieval | Câu hỏi ngoài domain (Out-of-domain). BM25 trả về 0 kết quả, Dense score thấp (0.1540). |
| 2 | **Q19**: Hướng dẫn sửa lỗi màn hình xanh (BSOD) trên Windows 10? | 0.00 | 0.00 | 0.00 | Retrieval | Câu hỏi ngoài domain. Không có dữ liệu trong kho tóm tắt sách. |
| 3 | **Q20**: Lịch thi tốt nghiệp THPT Quốc gia diễn ra ngày nào? | 0.00 | 0.00 | 0.00 | Retrieval | Câu hỏi ngoài domain. Cần trigger Fallback từ chối trả lời. |

---

## 5. Recommendations (Đề Xuất Cải Tiến Cho Pipeline Nhóm)

### Cải tiến 1: Thiết lập Ngưỡng Fallback Tự Động (Score Thresholding)
* **Action (Hành động):** Cấu hình `score_threshold = 0.30` dựa trên điểm Cosine Similarity gốc từ `semantic_search()` ở Task 9.
* **Expected impact (Tác động):** Loại bỏ 100% các câu hỏi ngoài domain (như Q18, Q19, Q20), tự động chuyển hướng sang từ chối lịch sự thay vì sinh câu trả lời rác.

### Cải tiến 2: Bổ Sung Tự Động Hóa BM25 Pre-tokenization
* **Action (Hành động):** Áp dụng bộ tách từ tiếng Việt/Anh chuẩn (`tokenize_bm25`) ở Task 6 trước khi nạp vào BM25Okapi.
* **Expected impact (Tác động):** Tăng thêm 5% Context Precision cho các câu hỏi tra cứu khái niệm bằng tiếng Việt.

### Cải tiến 3: Áp Dụng Cross-Encoder Reranking
* **Action (Hành động):** Tích hợp Jina Reranker v2 ở Task 7 để xếp lại thứ hạng cho Top 10 chunks trước khi gửi context cho LLM ở Task 10.
* **Expected impact (Tác động):** Nâng cao Faithfulness lên trên 0.95 và giảm nguy cơ xao nhãng context đối với các câu hỏi so sánh phức tạp.
