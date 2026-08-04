# Phân Công Công Việc Nhóm C3-02

> Nhóm trưởng: **Nguyễn Xuân Phượng**
>
> Ghi chú: Tài liệu này phân công theo đúng **6 role chuẩn** mà bạn đã chốt:
> - Role 1: Team Leader & RAG Architect
> - Role 2: Data Engineering & Scraping Dev
> - Role 3: Vector Database & Dense Search Dev
> - Role 4: Sparse Retrieval & Fallback Dev
> - Role 5: Frontend UI & App Integration Dev
> - Role 6: Evaluation & Benchmark QA Dev

## 1. Danh Sách Thành Viên

| Họ và tên | MSSV | Role | Nhiệm vụ chính |
|---|---:|---|---|
| Nguyễn Xuân Phượng | 2A202601874 | **Role 1** | Quản lý nhóm, kiến trúc Supervisor, điều phối demo |
| Phùng Hồng Phước | 2A202601215 | **Role 2** | Task 1, Task 2, Task 3 |
| Nguyễn Đào Nam Hải | 2A202601037 | **Role 3** | Task 4, Task 5 |
| Trần Đức Mạnh | 2A202601567 | **Role 4** | Task 6, Task 7, Task 8 |
| Lê Công Dũng | 2A202601649 | **Role 5** | Thiết kế app.py, Task 10 |
| Lê Nguyễn Minh Đức | 2A202601013 | **Role 6** | golden_dataset.json, RAGAS benchmark, results.md |

## 2. Luồng Phụ Thuộc Tổng Thể

Pipeline của nhóm nên đi theo thứ tự sau:

1. **Setup dự án và thống nhất cấu trúc thư mục**
2. **Task 1 - Task 2 - Task 3**: thu thập và chuẩn hoá dữ liệu
3. **Task 4**: chunking và indexing vào ChromaDB
4. **Task 5 - Task 6**: semantic search và lexical search
5. **Task 7 - Task 8**: RRF reranking và PageIndex fallback
6. **Task 9**: hợp nhất retrieval pipeline
7. **Task 10**: sinh câu trả lời có citation
8. **app.py**: tích hợp chatbot Streamlit
9. **golden_dataset.json / eval_pipeline.py / results.md**: đánh giá và báo cáo

### Sơ đồ phụ thuộc ngắn gọn

```text
Task 1, Task 2
    -> Task 3
        -> Task 4
            -> Task 5, Task 6
                -> Task 7, Task 8
                    -> Task 9
                        -> Task 10
                            -> app.py
                            -> evaluation / results.md
```

## 3. Phân Công Chi Tiết Theo Từng Người

### 3.1 Nguyễn Xuân Phượng - Nhóm trưởng, Role 1

#### Công việc chi tiết
1. Chốt phạm vi dữ liệu và tiêu chuẩn đầu ra cho cả nhóm.
2. Phân chia task, đặt deadline nội bộ và theo dõi tiến độ từng ngày.
3. Kiểm tra tính nhất quán giữa các module:
   - dữ liệu đầu vào
   - format markdown
   - format metadata
   - format citation
4. Thiết kế kiến trúc tổng thể của pipeline:
   - `Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5/6 -> Task 7/8 -> Task 9 -> Task 10 -> app.py`
5. Hợp nhất code cuối cùng từ các thành viên vào nhánh chung.
6. Kiểm tra demo, điều phối phần trình bày, và trả lời câu hỏi tổng quan về hệ thống.

#### Đầu ra cần có
- File mô tả kiến trúc nhóm
- Danh sách nhiệm vụ rõ ràng cho từng thành viên
- Bản tổng hợp code cuối
- Kế hoạch demo và checklist trước khi nộp

#### Phụ thuộc
- Cần nắm đầu ra từ tất cả các task còn lại để ghép hệ thống.
- Không thể hoàn tất phần kiến trúc nếu chưa có thống nhất về dữ liệu, retrieval, citation và evaluation.

---

### 3.2 Phùng Hồng Phước - Role 2: Data Engineering & Scraping Dev

#### Công việc chi tiết
1. **Task 1 - Tải PDF chính sách**
   - Tìm và tải ít nhất 3 tài liệu chính sách/quy định dạng PDF/DOCX.
   - Đặt tên file rõ ràng.
   - Lưu vào `data/landing/legal/`.
2. **Task 2 - Crawl bài viết tin tức**
   - Crawl ít nhất 5 bài viết hoặc thông báo liên quan đến dịch vụ đại học.
   - Lưu metadata: URL gốc, ngày crawl, tiêu đề.
   - Lưu vào `data/landing/news/`.
3. **Task 3 - Convert Markdown**
   - Chuyển toàn bộ file trong `data/landing/` sang Markdown.
   - Giữ nguyên cấu trúc thư mục con `legal/` và `news/`.
   - Đảm bảo file output nằm trong `data/standardized/`.
4. Kiểm tra lại dữ liệu đầu ra xem có lỗi định dạng, thiếu nội dung, hoặc metadata không đầy đủ không.
5. Báo cho Role 3 sau khi dữ liệu đã sẵn sàng để index.

#### Đầu ra cần có
- `data/landing/legal/*.pdf` hoặc `.docx`
- `data/landing/news/*.json` hoặc `.html`
- `data/standardized/legal/*.md`
- `data/standardized/news/*.md`

#### Phụ thuộc
- **Task 1** và **Task 2** có thể làm song song sau khi thống nhất nguồn dữ liệu.
- **Task 3** phụ thuộc vào việc hoàn thành **Task 1** và **Task 2**.
- Task 4 trở đi chỉ làm tốt nếu Task 3 đã chuẩn hoá dữ liệu xong.

---

### 3.3 Nguyễn Đào Nam Hải - Role 3: Vector Database & Dense Search Dev

#### Công việc chi tiết
1. **Task 4 - Chunking & ChromaDB Indexing**
   - Chọn chiến lược chunking phù hợp.
   - Thiết lập chunk size và overlap.
   - Tạo embeddings cho toàn bộ tài liệu Markdown.
   - Lưu vector store vào `chroma_db/`.
2. **Task 5 - Semantic Search**
   - Viết hàm truy vấn dense retrieval trên ChromaDB.
   - Trả về danh sách chunk kèm score và metadata.
3. **HyDE**
   - Nếu nhóm dùng HyDE, thêm bước sinh document giả định trước khi truy vấn vector store.
4. Test các câu hỏi mẫu để kiểm tra khả năng tìm đúng đoạn liên quan.
5. Ghi rõ thông số kỹ thuật:
   - embedding model
   - dimension
   - chunk size
   - overlap
   - lý do chọn cấu hình

#### Đầu ra cần có
- Thư mục `chroma_db/`
- Module semantic search hoạt động được
- Tài liệu ghi cấu hình index

#### Phụ thuộc
- **Task 4** phụ thuộc trực tiếp vào **Task 3**.
- **Task 5** phụ thuộc vào **Task 4**.
- Nếu dùng HyDE, vẫn cần dữ liệu đã chuẩn hoá tốt từ Task 3.

---

### 3.4 Trần Đức Mạnh - Role 4: Sparse Retrieval & Fallback Dev

#### Công việc chi tiết
1. **Task 6 - BM25 / TF-IDF**
   - Xây dựng lexical retrieval từ corpus Markdown.
   - Ưu tiên BM25, có thể bổ sung TF-IDF nếu cần so sánh.
2. **Task 7 - RRF Reranking**
   - Gộp kết quả từ dense search và sparse search bằng Reciprocal Rank Fusion.
   - Đảm bảo không cộng trực tiếp các loại score khác thang đo.
3. **Task 8 - PageIndex Fallback**
   - Tích hợp fallback cho các câu hỏi tổng hợp hoặc khó truy xuất bằng chunk-based retrieval.
   - Thiết kế điều kiện kích hoạt fallback rõ ràng.
4. Kiểm thử các tình huống:
   - câu hỏi có từ khoá chính xác
   - câu hỏi đồng nghĩa
   - câu hỏi tổng hợp nhiều phần
   - câu hỏi mà hybrid retrieval yếu

#### Đầu ra cần có
- Module lexical search
- Module reranking RRF
- Module fallback PageIndex

#### Phụ thuộc
- **Task 6** phụ thuộc vào corpus đã chuẩn hoá ở **Task 3**.
- **Task 7** phụ thuộc đồng thời vào **Task 5** và **Task 6**.
- **Task 8** có thể chuẩn bị song song với Task 6, nhưng khi tích hợp thật thì cần đi qua **Task 9**.

---

### 3.5 Lê Công Dũng - Role 5: Frontend UI & App Integration Dev

#### Công việc chi tiết
1. Thiết kế giao diện chatbot bằng Streamlit trong `app.py`.
2. Tổ chức layout:
   - ô chat
   - phần hiển thị câu trả lời
   - phần hiển thị citation / source documents
   - phần điều chỉnh tham số nếu có
3. Kết nối UI với pipeline retrieval và generation.
4. Kiểm tra trải nghiệm người dùng:
   - có thể hỏi tiếp câu follow-up
   - hiển thị nguồn rõ ràng
   - phản hồi nhanh, dễ đọc
5. Hỗ trợ chỉnh sửa phần format output để trả lời nhìn sạch và dễ demo.

#### Đầu ra cần có
- `app.py` chạy được bằng `streamlit run app.py`
- Giao diện chat hoàn chỉnh
- Hiển thị citation và nguồn tài liệu

#### Phụ thuộc
- Cần **Task 9** và **Task 10** xong thì mới nối UI ổn định.
- Nếu muốn demo tốt, UI nên được cập nhật sau khi retrieval pipeline đã chạy ổn.

---

### 3.6 Lê Nguyễn Minh Đức - Role 6: Evaluation & Benchmark QA Dev

#### Công việc chi tiết
1. Xây dựng hoặc mở rộng `golden_dataset.json` lên khoảng 20 câu hỏi.
2. Viết bộ câu hỏi bao phủ nhiều kiểu:
   - fact lookup
   - so sánh
   - câu hỏi tổng hợp
   - câu hỏi có từ khoá rõ
   - câu hỏi cần fallback
3. Chạy benchmark bằng RAGAS hoặc framework nhóm chọn.
4. Ghi kết quả vào `results.md`.
5. So sánh ít nhất 2 cấu hình nếu có:
   - dense-only
   - hybrid
   - hybrid + reranking
6. Rà soát chất lượng citation và độ khớp với context.
7. Hỗ trợ QA trước demo:
   - kiểm tra lỗi format
   - kiểm tra missing context
   - kiểm tra trường hợp câu trả lời sai nguồn

#### Đầu ra cần có
- `group_project/evaluation/golden_dataset.json`
- `group_project/evaluation/eval_pipeline.py`
- `group_project/evaluation/results.md`

#### Phụ thuộc
- Dataset đánh giá phải dựa trên tài liệu đã có ở **Task 3**.
- Benchmark chỉ có ý nghĩa đầy đủ khi **Task 9** và **Task 10** đã ổn định.

## 4. Phân Công Theo Bước Công Việc

### Bước 0 - Setup chung
**Người phụ trách:** Nguyễn Xuân Phượng  
**Phụ thuộc:** không có  
**Kết quả mong đợi:** cả nhóm cài xong môi trường, thống nhất `.env`, thống nhất branch và cấu trúc thư mục.

### Bước 1 - Task 1: Tải PDF chính sách
**Người phụ trách:** Phùng Hồng Phước  
**Phụ thuộc:** không có, chỉ cần thống nhất chủ đề dữ liệu  
**Kết quả mong đợi:** ít nhất 3 file chính sách gốc.

### Bước 2 - Task 2: Crawl bài viết tin tức
**Người phụ trách:** Phùng Hồng Phước  
**Phụ thuộc:** không có, nhưng nên thống nhất danh sách URL với nhóm trưởng  
**Kết quả mong đợi:** ít nhất 5 bài crawl có metadata đầy đủ.

### Bước 3 - Task 3: Convert Markdown
**Người phụ trách:** Phùng Hồng Phước  
**Phụ thuộc:** Task 1 + Task 2  
**Kết quả mong đợi:** toàn bộ dữ liệu có bản Markdown chuẩn trong `data/standardized/`.

### Bước 4 - Task 4: Chunking & Indexing
**Người phụ trách:** Nguyễn Đào Nam Hải  
**Phụ thuộc:** Task 3  
**Kết quả mong đợi:** `chroma_db/` được tạo thành công.

### Bước 5 - Task 5: Semantic Search
**Người phụ trách:** Nguyễn Đào Nam Hải  
**Phụ thuộc:** Task 4  
**Kết quả mong đợi:** truy vấn dense search chạy được.

### Bước 6 - Task 6: BM25 / TF-IDF
**Người phụ trách:** Trần Đức Mạnh  
**Phụ thuộc:** Task 3  
**Kết quả mong đợi:** truy vấn lexical search chạy được.

### Bước 7 - Task 7: RRF Reranking
**Người phụ trách:** Trần Đức Mạnh  
**Phụ thuộc:** Task 5 + Task 6  
**Kết quả mong đợi:** gộp thứ hạng đúng logic, không cộng score sai thang đo.

### Bước 8 - Task 8: PageIndex Fallback
**Người phụ trách:** Trần Đức Mạnh  
**Phụ thuộc:** Task 3, và khi tích hợp đầy đủ thì nối với Task 9  
**Kết quả mong đợi:** fallback hoạt động khi hybrid retrieval yếu.

### Bước 9 - Task 9: Retrieval Pipeline tổng
**Người phụ trách:** Nguyễn Xuân Phượng phối hợp với Nam Hải và Đức Mạnh  
**Phụ thuộc:** Task 5 + Task 6 + Task 7 + Task 8  
**Kết quả mong đợi:** pipeline retrieval hoàn chỉnh.

### Bước 10 - Task 10: Generation có citation
**Người phụ trách:** Lê Công Dũng phối hợp với nhóm trưởng  
**Phụ thuộc:** Task 9  
**Kết quả mong đợi:** sinh câu trả lời có trích dẫn nguồn rõ ràng.

### Bước 11 - app.py: Tích hợp chatbot UI
**Người phụ trách:** Lê Công Dũng  
**Phụ thuộc:** Task 10  
**Kết quả mong đợi:** chatbot Streamlit chạy được end-to-end.

### Bước 12 - Evaluation
**Người phụ trách:** Lê Nguyễn Minh Đức  
**Phụ thuộc:** Task 9 + Task 10 + dữ liệu chuẩn hóa  
**Kết quả mong đợi:** bộ golden dataset, báo cáo benchmark, và `results.md`.

## 5. Gợi Ý Cách Phối Hợp Giữa Các Thành Viên

1. Nhóm trưởng chốt tiêu chuẩn đặt tên file và format metadata ngay từ đầu.
2. Data team bàn giao xong thì Dense Search và Sparse Search cùng bắt đầu.
3. Retrieval team phải thống nhất format output để UI và Generation dùng chung.
4. Evaluation chỉ nên chạy trên bản pipeline đã “đóng băng” tương đối, tránh đổi code liên tục làm kết quả benchmark khó so sánh.
5. Trước demo, cả nhóm cần test theo 3 luồng:
   - câu hỏi dễ
   - câu hỏi cần hybrid retrieval
   - câu hỏi cần fallback

## 6. Checklist Nộp Bài

- [ ] Đủ file dữ liệu gốc trong `data/landing/`
- [ ] Đủ file Markdown trong `data/standardized/`
- [ ] `chroma_db/` tạo thành công
- [ ] Semantic search và BM25 hoạt động
- [ ] RRF reranking và PageIndex fallback chạy được
- [ ] `app.py` trả lời có citation
- [ ] `golden_dataset.json` đủ số lượng câu hỏi
- [ ] `results.md` có bảng điểm và nhận xét
- [ ] README hoặc file nhóm mô tả rõ phân công
- [ ] Demo chạy được trước khi nộp

---

Nếu bạn muốn, mình có thể làm tiếp một bản **ngắn gọn hơn để dán thẳng vào README** hoặc **vẽ thêm sơ đồ Mermaid** cho phần phụ thuộc giữa các task.  
