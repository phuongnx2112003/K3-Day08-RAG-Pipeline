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

## 3. Phân Công Theo Checkpoint

> Quy ước áp dụng: nhóm ưu tiên **Phương án C - nhóm 6 người** trong `LAB_GUIDE.md` để xác định quyền sở hữu Task 1-10. Một số dòng role ở phần checkpoint của lab là mô tả tổng quát cho nhóm quy mô khác, nên chỉ dùng làm checklist tiến độ. **Task 9** được giao cho Phượng (Role 1) vì đây là bước hợp nhất kiến trúc giữa dense retrieval của Role 3 và sparse/fallback của Role 4; **Task 10** vẫn thuộc Dũng (Role 5). Việc này không thay đổi 6 role đã chốt.

### CP0 - Setup Môi Trường (0:00 - 0:10)

| Thành viên | Nhiệm vụ | Phụ thuộc / Bàn giao |
|---|---|---|
| Phượng - Role 1 | Kiểm tra repo chung, tạo quy ước branch, chốt chủ đề dữ liệu, kiểm tra `.env.example` và phân công. | Không phụ thuộc; bàn giao cấu trúc dự án và danh sách nguồn dữ liệu. |
| Phước - Role 2 | Tạo môi trường ảo, cài dependencies; kiểm tra thư viện crawl và MarkItDown. | Báo lỗi cài đặt cho Phượng trước CP1. |
| Hải - Role 3 | Kiểm tra `chromadb`, `sentence-transformers` và khả năng tải embedding model. | Sẵn sàng môi trường cho CP2. |
| Mạnh - Role 4 | Kiểm tra `rank-bm25`, cấu hình `PAGEINDEX_API_KEY` nếu nhóm sử dụng PageIndex. | Báo tình trạng API/fallback cho Phượng. |
| Dũng - Role 5 | Kiểm tra Streamlit chạy được và xác nhận biến API cho Task 10. | Sẵn sàng khung `app.py` cho CP5. |
| Minh Đức - Role 6 | Kiểm tra `ragas`, `datasets`; tạo cấu trúc file evaluation. | Sẵn sàng template benchmark cho CP5. |

**Điều kiện qua CP0:** mọi người cài được dependencies cần cho role của mình và thống nhất cách chạy dự án bằng `python3`.

### CP1 - Thu Thập Và Chuẩn Hóa Dữ Liệu (0:10 - 0:35)

| Thành viên | Nhiệm vụ | Phụ thuộc / Bàn giao |
|---|---|---|
| Phượng - Role 1 | Duyệt danh sách URL, tránh tài liệu trùng lặp; kiểm tra số lượng và chất lượng đầu ra. | Nhận báo cáo từ Phước. |
| Phước - Role 2 | Làm Task 1, 2, 3: tải ít nhất 3 PDF/DOCX, crawl ít nhất 5 bài có metadata, convert toàn bộ sang Markdown. | Bàn giao `data/standardized/` cho Hải và Mạnh. |
| Hải - Role 3 | Xem trước Markdown, phản hồi nếu thiếu `source`, `type` hoặc nội dung quá ngắn gây khó index. | Phụ thuộc Role 2 hoàn thành Markdown. |
| Mạnh - Role 4 | Kiểm tra corpus có thể tokenize cho BM25; đề xuất chuẩn hóa text nếu cần. | Phụ thuộc Role 2 hoàn thành Markdown. |
| Dũng - Role 5 | Chuẩn bị câu hỏi gợi ý trong UI dựa trên tài liệu thực tế. | Nhận danh sách chủ đề từ Role 2. |
| Minh Đức - Role 6 | Soạn nháp 20 câu hỏi golden dataset, mỗi câu phải có evidence dự kiến trong nguồn đã crawl. | Hoàn thiện sau khi Role 2 bàn giao data. |

**Điều kiện qua CP1:** có ít nhất 3 file chính sách, 5 bài tin và Markdown tương ứng trong `data/standardized/`.

### CP2 - Chunking, Indexing Và Search Cơ Bản (0:35 - 1:00)

| Thành viên | Nhiệm vụ | Phụ thuộc / Bàn giao |
|---|---|---|
| Phượng - Role 1 | Duyệt contract chunk chung: `content`, `score`, `metadata`; chốt `CHUNK_SIZE=800`, `CHUNK_OVERLAP=100` và model embedding với Hải. | Phụ thuộc Markdown của CP1. |
| Phước - Role 2 | Sửa hoặc bổ sung data nếu phát hiện file rỗng, lỗi encode hay metadata thiếu. | Hỗ trợ Hải/Mạnh theo phản hồi. |
| Hải - Role 3 | Làm Task 4 và 5: chunking, ChromaDB indexing, `semantic_search()` và HyDE nếu triển khai. | Nhận Markdown từ Role 2; bàn giao dense results cho Mạnh/Phượng. |
| Mạnh - Role 4 | Làm Task 6: xây BM25/TF-IDF từ cùng corpus và trả format chunk thống nhất. | Nhận Markdown từ Role 2; đối chiếu format với Hải. |
| Dũng - Role 5 | Chuẩn bị UI nhận `answer`, `sources`; chưa nối pipeline khi Task 10 chưa xong. | Nhận contract output từ Phượng. |
| Minh Đức - Role 6 | Chọn 5 câu sanity-check để đo dense và BM25 có lấy đúng context hay không. | Nhận kết quả từ Hải và Mạnh. |

**Điều kiện qua CP2:** tạo được ChromaDB với `CHUNK_SIZE=800`, `CHUNK_OVERLAP=100`; `semantic_search()` và `lexical_search()` trả danh sách chunks đúng contract.

### CP3 - Reranking Và Vectorless Fallback (1:00 - 1:20)

| Thành viên | Nhiệm vụ | Phụ thuộc / Bàn giao |
|---|---|---|
| Phượng - Role 1 | Kiểm tra RRF dùng rank, không cộng trực tiếp score; thống nhất tiêu chí fallback dùng cosine gốc. | Nhận kết quả dense/sparse từ Hải và Mạnh. |
| Phước - Role 2 | Hỗ trợ cung cấp hoặc làm sạch tài liệu phù hợp để upload PageIndex nếu cần. | Theo yêu cầu của Mạnh. |
| Hải - Role 3 | Cung cấp score cosine gốc từ dense search để Task 9 quyết định fallback chính xác. | Bàn giao cho Mạnh và Phượng. |
| Mạnh - Role 4 | Làm Task 7 và 8: `rerank_rrf()`, PageIndex fallback, kiểm thử câu hỏi ngoài domain. | Task 7 phụ thuộc Task 5 + Task 6; bàn giao các hàm cho Phượng. |
| Dũng - Role 5 | Chuẩn bị cách hiển thị nhãn `hybrid` hoặc `pageindex` trên UI. | Nhận format result từ Mạnh. |
| Minh Đức - Role 6 | Thêm câu hỏi khó/ngoài domain vào golden dataset để test fallback. | Nhận behavior fallback từ Mạnh. |

**Điều kiện qua CP3:** RRF gộp được Dense + BM25 và fallback không sử dụng score RRF làm ngưỡng.

### CP4 - Pipeline Hoàn Chỉnh Và Citation (1:20 - 1:45)

| Thành viên | Nhiệm vụ | Phụ thuộc / Bàn giao |
|---|---|---|
| Phượng - Role 1 | Làm Task 9, ghép Semantic + BM25 + RRF + PageIndex vào `retrieve()`; kiểm tra `PipelineSupervisor`, chạy `pytest tests/test_individual.py -v` và xử lý lỗi tích hợp. | Phụ thuộc Task 5-8; bàn giao retrieval contract cho Dũng/Minh Đức. |
| Phước - Role 2 | Hỗ trợ đối chiếu kết quả retrieval với tài liệu gốc khi có lỗi. | Nhận query lỗi từ Phượng. |
| Hải - Role 3 | Hỗ trợ chỉnh semantic score/HyDE nếu fallback kích hoạt sai. | Theo log tích hợp Task 9. |
| Mạnh - Role 4 | Hỗ trợ sửa RRF, BM25 hoặc PageIndex nếu Task 9 không ghép được. | Theo log tích hợp Task 9. |
| Dũng - Role 5 | Làm Task 10: reorder chunks, format context, gọi LLM và trả citation cùng sources. | Phụ thuộc `retrieve()` của Role 1. |
| Minh Đức - Role 6 | Rà citation: mỗi claim phải bám context; ghi các case trả lời không đủ evidence. | Phụ thuộc Task 10. |

**Điều kiện qua CP4:** `retrieve()` và `generate_with_citation()` chạy theo contract; câu trả lời có citation hoặc từ chối khi evidence thiếu; `pytest tests/test_individual.py -v` đạt toàn bộ test khả dụng.

### CP5 - Chatbot Và Đánh Giá RAGAS (1:45 - 2:15)

| Thành viên | Nhiệm vụ | Phụ thuộc / Bàn giao |
|---|---|---|
| Phượng - Role 1 | Ghép code cuối, chạy health check, theo dõi lỗi tích hợp và duyệt checklist demo. | Phụ thuộc Task 9/10 hoạt động. |
| Phước - Role 2 | Bổ sung nguồn nếu benchmark chỉ ra thiếu evidence cho nhóm câu hỏi quan trọng. | Nhận phân tích từ Minh Đức. |
| Hải - Role 3 | Hỗ trợ cấu hình dense-only cho so sánh A/B. | Phối hợp Minh Đức. |
| Mạnh - Role 4 | Hỗ trợ cấu hình hybrid/reranking cho so sánh A/B. | Phối hợp Minh Đức. |
| Dũng - Role 5 | Hoàn thiện `app.py`: lịch sử chat, top_k, câu hỏi gợi ý, citation và source documents. | Phụ thuộc Task 10 và Supervisor contract. |
| Minh Đức - Role 6 | Hoàn thiện 20 câu golden dataset, chạy RAGAS, so sánh A/B và viết `results.md`. | Phụ thuộc pipeline ổn định; bàn giao báo cáo cho Phượng. |

**Điều kiện qua CP5:** chatbot chạy được, hiển thị nguồn; báo cáo có metrics và bảng so sánh A/B.

### CP6 - Thuyết Trình Và Nộp Bài (2:15 - 3:00)

| Thành viên | Nhiệm vụ | Phụ thuộc / Bàn giao |
|---|---|---|
| Phượng - Role 1 | Dẫn dắt demo, giới thiệu kiến trúc, điều phối người trình bày, kiểm tra repo và deliverables trước nộp. | Nhận xác nhận hoàn thành từ cả nhóm. |
| Phước - Role 2 | Trình bày nguồn, crawling, metadata và Markdown. | Dựa trên output CP1. |
| Hải - Role 3 | Trình bày chunking, ChromaDB, dense search và HyDE. | Dựa trên output CP2. |
| Mạnh - Role 4 | Trình bày BM25, RRF và lý do fallback dùng cosine gốc. | Dựa trên output CP3-4. |
| Dũng - Role 5 | Chạy Streamlit live demo, chỉ ra citation và source documents. | Dựa trên output CP5. |
| Minh Đức - Role 6 | Trình bày golden dataset, RAGAS, kết quả A/B và hướng cải thiện. | Dựa trên output CP5. |

**Điều kiện qua CP6:** repo có đủ code, data, README, báo cáo evaluation và demo chạy được tại máy trình bày.

## 4. Phân Công Chi Tiết Theo Từng Người

### 4.1 Nguyễn Xuân Phượng - Nhóm trưởng, Role 1

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

### 4.2 Phùng Hồng Phước - Role 2: Data Engineering & Scraping Dev

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

### 4.3 Nguyễn Đào Nam Hải - Role 3: Vector Database & Dense Search Dev

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

### 4.4 Trần Đức Mạnh - Role 4: Sparse Retrieval & Fallback Dev

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

### 4.5 Lê Công Dũng - Role 5: Frontend UI & App Integration Dev

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

### 4.6 Lê Nguyễn Minh Đức - Role 6: Evaluation & Benchmark QA Dev

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

## 5. Phân Công Theo Bước Công Việc

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

## 6. Gợi Ý Cách Phối Hợp Giữa Các Thành Viên

1. Nhóm trưởng chốt tiêu chuẩn đặt tên file và format metadata ngay từ đầu.
2. Data team bàn giao xong thì Dense Search và Sparse Search cùng bắt đầu.
3. Retrieval team phải thống nhất format output để UI và Generation dùng chung.
4. Evaluation chỉ nên chạy trên bản pipeline đã “đóng băng” tương đối, tránh đổi code liên tục làm kết quả benchmark khó so sánh.
5. Trước demo, cả nhóm cần test theo 3 luồng:
   - câu hỏi dễ
   - câu hỏi cần hybrid retrieval
   - câu hỏi cần fallback

## 7. Checklist Nộp Bài

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
