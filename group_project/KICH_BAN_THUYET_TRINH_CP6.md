# Kịch bản thuyết trình CP6 — Book Insights Hybrid RAG

> Tài liệu dùng chung cho 6 thành viên. Nội dung bên dưới bám theo trạng thái code thực tế của repo ngày 04/08/2026. Không đọc các phần ghi chú trong ngoặc vuông khi thuyết trình.

## 1. Tóm tắt kiến trúc đã dùng

```text
4 PDF + 5 bài web có metadata
             │
             ▼
     9 tài liệu Markdown chuẩn hóa
             │
             ▼
RecursiveCharacterTextSplitter
size = 800, overlap = 100
             │
             ├───────────────┐
             ▼               ▼
 ChromaDB + Jina v3       BM25 / TF-IDF
 Dense retrieval          Sparse retrieval
 cosine gốc               keyword score
             │               │
             └───────┬───────┘
                     ▼
              RRF reranking, k = 60
                     │
        top dense cosine < 0.40?
              ┌──────┴──────┐
             không           có
              │              ▼
              │       PageIndex fallback
              └──────┬───────┘
                     ▼
       Reorder context → OpenAI Responses API
                     ▼
       Câu trả lời tiếng Việt + [S1], [S2]...
                     ▼
        Streamlit + source documents
                     ▼
       Golden dataset 20 câu + RAGAS A/B
```

Các module chính:

| Khối | File | Vai trò |
|---|---|---|
| Thu thập PDF | `src/task1_collect_legal_docs.py` | Lưu tài liệu gốc vào `data/landing/legal/` |
| Crawl bài web | `src/task2_crawl_news.py` | Lưu nội dung và metadata dạng JSON |
| Chuẩn hóa | `src/task3_convert_markdown.py` | Chuyển toàn bộ corpus sang Markdown |
| Chunk và index | `src/task4_chunking_indexing.py` | Tạo chunks và index vào ChromaDB |
| Dense search | `src/task5_semantic_search.py` | Tìm theo vector, trả cosine gốc |
| Sparse search | `src/task6_lexical_search.py` | BM25/TF-IDF trên cùng corpus |
| Rerank | `src/task7_reranking.py` | Reciprocal Rank Fusion |
| Fallback | `src/task8_pageindex_vectorless.py` | Truy hồi PageIndex khi dense yếu |
| Pipeline | `src/task9_retrieval_pipeline.py` | Ghép Dense + BM25 + RRF + fallback |
| Generation | `src/task10_generation.py` | Sinh trả lời grounded và citation |
| Điều phối | `src/supervisor.py` | Contract chung và health check |
| Giao diện | `app.py` | Chatbot Streamlit |
| Đánh giá | `group_project/evaluation/` | Golden dataset, RAGAS và A/B |

## 2. Kịch bản tổng thể đề xuất

Thời lượng mục tiêu: 10–12 phút.

| Người trình bày | Nội dung | Thời lượng |
|---|---|---:|
| Phượng | Bài toán, kiến trúc, điều phối | 1 phút 30 giây |
| Phước | Nguồn dữ liệu, crawl, metadata, Markdown | 1 phút 30 giây |
| Hải | Chunking, ChromaDB, dense search, HyDE | 1 phút 30 giây |
| Mạnh | BM25, RRF, fallback bằng cosine gốc | 2 phút |
| Dũng | Streamlit live demo, citation, sources | 2 phút 30 giây |
| Minh Đức | Golden dataset, RAGAS, A/B, cải thiện | 2 phút |
| Phượng | Kết luận và nhận câu hỏi | 30 giây |

## 3. Phượng — Role 1: Mở đầu, kiến trúc và điều phối

### Lời thoại

“Xin chào thầy/cô và các bạn. Nhóm C3-02 triển khai **Trợ lý Review và Tóm tắt sách chuyên sâu** bằng kiến trúc Hybrid RAG. Mục tiêu của hệ thống là trả lời câu hỏi về các cuốn sách trong corpus, đồng thời mỗi nhận định phải đi kèm citation để người dùng kiểm tra lại nguồn.”

“Pipeline của nhóm có ba lớp chính. Lớp dữ liệu thu thập PDF và bài viết web rồi chuẩn hóa thành Markdown. Lớp retrieval chạy song song dense search trên ChromaDB và sparse search bằng BM25, sau đó hợp nhất thứ hạng bằng RRF. Nếu cosine gốc của dense search thấp hơn 0.40, hệ thống chuyển sang PageIndex; nếu vẫn không có bằng chứng thì từ chối trả lời. Cuối cùng, OpenAI sinh câu trả lời từ context đã truy hồi và gắn citation `[S1]`, `[S2]`.”

“Các module được nối bằng một contract thống nhất gồm `content`, `score`, `metadata`. `PipelineSupervisor` cung cấp một đầu vào ổn định cho UI và evaluation, đồng thời kiểm tra Task 9 và Task 10 đã sẵn sàng trước demo.”

“Sau đây, Phước sẽ trình bày cách nhóm xây dựng corpus đầu vào.”

### Điểm cần chỉ trên slide/repo

- Sơ đồ kiến trúc ở đầu tài liệu này.
- `src/supervisor.py`.
- Health check phải hiện hai dòng `READY`.

### Lệnh kiểm tra trước demo

```powershell
.\.venv\Scripts\python.exe -m src.supervisor
```

Kết quả kỳ vọng:

```text
[READY] retrieval pipeline (Task 9): Worker contract is available
[READY] citation generation (Task 10): Worker contract is available
```

## 4. Phước — Role 2: Nguồn, crawling, metadata và Markdown

### Lời thoại

“Corpus hiện có **9 tài liệu**, gồm **4 PDF** và **5 bài viết web**. Chủ đề bao phủ Atomic Habits, The Lean Startup, Thinking, Fast and Slow và The Innovators. PDF được lưu trong `data/landing/legal`, còn dữ liệu crawl được lưu trong `data/landing/news` dưới dạng JSON.”

“Với mỗi bài crawl, nhóm không chỉ lấy nội dung mà còn giữ metadata như URL nguồn, tiêu đề, tác giả, tên sách, category, type và thời điểm crawl. Metadata rất quan trọng vì nó được truyền xuyên suốt pipeline để phục vụ truy vết và hiển thị source documents.”

“Task 3 chuyển toàn bộ dữ liệu sang **9 file Markdown** trong `data/standardized`. Mỗi file có phần header metadata và nội dung phía dưới. Markdown được chọn vì dễ kiểm tra bằng mắt, giữ được heading và thuận tiện cho chunking.”

“Nhóm cũng kiểm tra UTF-8, Unicode NFKC, control characters và whitespace. Kết quả audit cho thấy cả 9 trên 9 file có thể tokenize cho BM25, với tổng khoảng **21.777 token** sau chuẩn hóa.”

“Tiếp theo, Hải sẽ trình bày cách các tài liệu này được chunk và index cho dense retrieval.”

### Demo nhanh

Mở một file, ví dụ:

```text
data/standardized/news/article_01.md
```

Chỉ vào các trường:

```text
Source, Crawled, Book, Author, Category, Type
```

### Nếu bị hỏi “metadata để làm gì?”

Trả lời: “Metadata giúp nhận diện chunk, loại trùng khi RRF, truy vết về tài liệu gốc và hiển thị title, author, URL trong citation. Nội dung dùng để tìm kiếm, metadata dùng để giải thích nguồn gốc của kết quả.”

## 5. Hải — Role 3: Chunking, ChromaDB, dense search và HyDE

### Lời thoại

“Từ 9 file Markdown, nhóm sử dụng `RecursiveCharacterTextSplitter` với `chunk_size = 800` và `chunk_overlap = 100`. Overlap giúp thông tin ở ranh giới hai chunk không bị mất. Kết quả hiện tại là **229 chunks**.”

“Mỗi chunk giữ ba trường chung: `content`, `score` và `metadata`; metadata quan trọng nhất gồm `source`, `type`, `chunk_index`. Các chunk được embedding bằng **Jina Embeddings v3**, vector **1024 chiều**, rồi lưu trong collection ChromaDB `university_services_docs`.”

“Khi có câu hỏi, Task 5 tạo query embedding và tìm các vector gần nhất. Hàm trả cosine similarity theo thứ tự giảm dần. Với câu hỏi về Four Laws của Atomic Habits, dense search đã lấy đúng tài liệu với cosine khoảng 0.70 trong lần hiệu chỉnh.”

“Về HyDE: HyDE là kỹ thuật để LLM tạo một câu trả lời giả định rồi embedding câu trả lời đó thay cho câu hỏi ngắn. Cách này có thể cải thiện semantic retrieval khi query và tài liệu khác cách diễn đạt. Tuy nhiên, **repo hiện tại đang dùng direct query embedding và chưa bật HyDE trong luồng production**. Đây là hướng mở rộng, không phải kết quả mà nhóm đã chạy.”

“Tiếp theo, Mạnh sẽ giải thích vì sao nhóm vẫn cần BM25, cách kết hợp hai retriever bằng RRF và cơ chế fallback.”

### Điểm kỹ thuật phải nhớ

- Chunk size: 800 ký tự.
- Overlap: 100 ký tự.
- Tổng chunks: 229.
- Embedding: `jina-embeddings-v3`, 1024 chiều.
- Vector store: ChromaDB local.
- HyDE chưa được kích hoạt trong code hiện tại; không nói là đã benchmark HyDE.

### Nếu bị hỏi “vì sao cần overlap?”

Trả lời: “Nếu một khái niệm nằm sát biên chunk, cắt không overlap có thể tách câu hỏi khỏi phần giải thích. Overlap 100 ký tự tạo vùng giao nhau để tăng khả năng giữ đủ ngữ cảnh.”

## 6. Mạnh — Role 4: BM25, RRF và fallback dùng cosine gốc

### Lời thoại

“Dense search mạnh về ngữ nghĩa nhưng có thể bỏ sót tên riêng, thuật ngữ hoặc cụm từ chính xác. Vì vậy Task 6 xây **BM25 và TF-IDF trên đúng 229 chunks** đã dùng cho ChromaDB. Tokenizer dùng Unicode NFKC, casefold nhưng vẫn giữ dấu tiếng Việt, số và từ ghép. BM25 chạy với `k1 = 1.5`, `b = 0.75`.”

“Dense và BM25 có thang điểm hoàn toàn khác nhau: cosine thường nằm trong khoảng 0 đến 1, còn BM25 có thể lớn hơn nhiều. Vì vậy nhóm không cộng trực tiếp hai score. Task 7 dùng **Reciprocal Rank Fusion**, viết tắt RRF, theo công thức: `RRF(d) = tổng 1 / (k + rank)` với `k = 60`. RRF chỉ quan tâm thứ hạng, nên hai retriever có thể đóng góp công bằng mà không cần chuẩn hóa score.”

“Ví dụ, nếu một chunk đứng hạng 1 ở cả dense và BM25 thì RRF score là `1/61 + 1/61 = 0.03278689`. Chunk xuất hiện cao ở cả hai danh sách sẽ được ưu tiên.”

“Điểm quan trọng nhất là **không dùng RRF score để quyết định fallback**. RRF luôn cho điểm dựa trên vị trí; ngay cả một danh sách kết quả kém liên quan vẫn có phần tử hạng 1. Vì vậy RRF score không biểu diễn độ giống tuyệt đối giữa câu hỏi và tài liệu.”

“Nhóm dùng cosine gốc cao nhất từ dense retrieval. Kết quả hiệu chỉnh cho thấy ba câu in-domain có cosine từ **0.6255 đến 0.7264**, trong khi bốn câu out-of-domain chỉ từ **0.0756 đến 0.1804**. Nhóm chọn ngưỡng ban đầu **0.40**, nằm giữa hai vùng này.”

“Nếu top cosine dưới 0.40, Task 9 gọi PageIndex trên PDF tổng hợp của corpus. PageIndex tìm theo cấu trúc tài liệu mà không phụ thuộc vector store. Nếu PageIndex cũng không tìm được evidence, pipeline trả danh sách rỗng để Task 10 từ chối, thay vì cố trả lời bằng context yếu.”

“Sau đây, Dũng sẽ chạy toàn bộ pipeline trên giao diện Streamlit và chỉ ra citation.”

### Bảng số liệu nên đưa lên slide

| Nhóm query | Khoảng top cosine đã đo |
|---|---:|
| In-domain | 0.6255–0.7264 |
| Out-of-domain | 0.0756–0.1804 |
| Ngưỡng fallback | 0.40 |

### Nếu bị hỏi “BM25 và TF-IDF khác gì?”

Trả lời: “TF-IDF biểu diễn độ quan trọng của từ rồi so cosine; BM25 bổ sung cơ chế bão hòa tần suất từ và chuẩn hóa độ dài tài liệu. Vì thế BM25 thường phù hợp hơn cho search và được dùng mặc định; TF-IDF được giữ để benchmark.”

### Nếu bị hỏi “PageIndex có phải web search không?”

Trả lời: “Không. PageIndex chỉ truy hồi trên PDF corpus mà nhóm đã upload. Nó là một fallback vectorless trên chính dữ liệu nội bộ, không lấy thông tin tùy ý từ Internet.”

## 7. Dũng — Role 5: Streamlit live demo, citation và sources

### Chuẩn bị

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Đảm bảo sidebar hiển thị `Task 9/10 READY`.

### Lời thoại

“Đây là giao diện chatbot Streamlit. Sidebar có câu hỏi gợi ý, `top_k`, ngưỡng fallback cosine, nút xóa lịch sử và health status của Task 9/10. Luồng phía sau là Dense plus BM25, RRF, PageIndex fallback, sau đó OpenAI sinh câu trả lời có citation.”

“Tôi sẽ thử câu hỏi in-domain: **Phương pháp 4 bước xây dựng thói quen theo Atomic Habits là gì?** Hệ thống truy hồi evidence, reorder context để giảm hiện tượng lost-in-the-middle và gửi context cho OpenAI Responses API.”

“Trong câu trả lời, mỗi claim có nhãn như `[S1]` hoặc `[S2]`. Bên dưới, mục Nguồn tham khảo hiển thị đúng citation ID, tiêu đề, tác giả, URL, phương thức retrieval, score và đoạn evidence đã dùng. Nhờ vậy người dùng có thể kiểm tra lại câu trả lời.”

“Tiếp theo tôi thử câu ngoài domain: **Giá Bitcoin hôm nay là bao nhiêu?** Dense cosine thấp sẽ kích hoạt fallback. PageIndex không có evidence về giá Bitcoin, nên chatbot trả: **Tôi không thể xác minh thông tin này từ nguồn hiện có.** Đây là behavior có chủ ý để hạn chế hallucination.”

“Cuối cùng, Minh Đức sẽ trình bày cách nhóm đánh giá có hệ thống thay vì chỉ dựa vào vài câu demo.”

### Thứ tự demo an toàn

1. Chỉ sidebar báo `Task 9/10 READY`.
2. Chạy câu Atomic Habits.
3. Chỉ citation trong answer.
4. Mở expander `Nguồn tham khảo` và đối chiếu `[S1]`.
5. Chạy câu Bitcoin để minh họa refusal.

### Phương án dự phòng nếu API lỗi

- Không xóa hoặc rebuild `chroma_db/` ngay trước demo.
- Chụp sẵn ảnh một câu trả lời thành công và trang sources.
- Nếu OpenAI lỗi, vẫn có thể chạy retrieval test và giải thích rằng generation là external dependency.
- Nếu PageIndex timeout, dùng câu Bitcoin và giải thích pipeline trả `[]` an toàn thay vì dựng evidence giả.

## 8. Minh Đức — Role 6: Golden dataset, RAGAS, A/B và cải thiện

### Lời thoại

“Để đánh giá, nhóm xây golden dataset gồm **20 câu**: **18 câu in-domain** và **2 câu out-of-domain**. Các câu bao phủ fact, concept, explanation, process, application, bias, analysis, summary và refusal. Mỗi mẫu có question, expected answer, expected context, expected sources, category và cờ `should_answer`.”

“Nhóm dùng bốn metric RAGAS. **Faithfulness** đo câu trả lời có bám evidence không. **Answer relevancy** đo câu trả lời có đúng trọng tâm câu hỏi không. **Context recall** đo retriever có lấy đủ thông tin cần thiết không. **Context precision** đo các context được lấy có thật sự hữu ích và được xếp hợp lý không.”

“Cấu hình A là `hybrid + RRF + PageIndex fallback`. Cấu hình B là `dense-only`, tắt reranking và tắt fallback để tạo baseline công bằng. Cả hai dùng cùng golden dataset, top-k và generation model; như vậy khác biệt chủ yếu đến từ retrieval.”

“[CHỈ ĐỌC SAU KHI ĐÃ CHẠY EVALUATION] Kết quả A/B được lấy trực tiếp từ `group_project/evaluation/results.md`. Config có điểm trung bình cao hơn là ______. Metric cải thiện rõ nhất là ______, thay đổi ______ điểm. Ba câu yếu nhất là ______; nguyên nhân chính nằm ở bước ______.”

“Từ phân tích lỗi, nhóm đề xuất ba hướng cải thiện. Một là bổ sung tóm tắt tiếng Việt hoặc query expansion Việt–Anh để BM25 xử lý tốt corpus tiếng Anh. Hai là hiệu chỉnh threshold trên tập validation lớn hơn, thay vì chỉ một vài câu calibration. Ba là bổ sung tài liệu còn thiếu, cải thiện metadata và thử HyDE hoặc reranker học máy cho các truy vấn diễn đạt gián tiếp.”

“Em xin chuyển lại cho Phượng tổng kết.”

### Bốn metric cần nhớ

| Metric | Câu hỏi metric trả lời |
|---|---|
| Faithfulness | Answer có bịa ngoài context không? |
| Answer relevancy | Answer có trả lời đúng câu hỏi không? |
| Context recall | Retrieval có lấy đủ evidence cần thiết không? |
| Context precision | Các context lấy về có liên quan và hữu ích không? |

### Quy tắc bắt buộc khi trình bày kết quả

- Không tự điền số nếu `results.md` chưa có kết quả chạy thật.
- Nêu rõ model judge, ngày chạy, số mẫu và cấu hình A/B.
- Nếu chỉ chạy subset vì rate limit, phải nói đúng số câu đã chạy; không gọi đó là full 20 câu.
- Tách lỗi retrieval khỏi lỗi generation khi phân tích bottom cases.

## 9. Phượng — Kết luận

### Lời thoại

“Tóm lại, nhóm đã xây dựng một pipeline RAG có thể truy vết từ dữ liệu gốc đến citation cuối cùng. Điểm chính của kiến trúc là kết hợp semantic và lexical retrieval bằng rank fusion, chỉ fallback theo cosine gốc đã hiệu chỉnh, và từ chối khi không có bằng chứng. Hệ thống được đóng gói trong Streamlit và có golden dataset để đánh giá A/B. Nhóm em xin cảm ơn và sẵn sàng nhận câu hỏi.”

## 10. Câu hỏi phản biện thường gặp

### Tại sao không chỉ dùng dense search?

Dense search hiểu ngữ nghĩa tốt nhưng có thể bỏ sót thuật ngữ, tên riêng hoặc exact match. BM25 bù cho điểm yếu đó; RRF kết hợp thứ hạng mà không cần ép hai loại score về cùng một thang đo.

### Tại sao threshold là 0.40?

Đây là ngưỡng calibration ban đầu. Trong mẫu đã đo, out-of-domain cao nhất là 0.1804 và in-domain thấp nhất là 0.6255; 0.40 nằm giữa hai vùng. Khi có nhiều dữ liệu validation hơn, threshold cần được tối ưu tiếp.

### Tại sao không dùng RRF score cho fallback?

RRF phản ánh thứ hạng tương đối, không phản ánh độ liên quan tuyệt đối. Mọi danh sách đều có một phần tử hạng 1, kể cả khi toàn bộ kết quả đều kém. Cosine gốc phù hợp hơn để so với ngưỡng relevance.

### Citation có bảo đảm mọi câu đều đúng không?

Không tuyệt đối. Citation tăng khả năng kiểm chứng và prompt buộc model chỉ dùng context. Code còn kiểm tra ID citation có nằm trong danh sách nguồn hay không. Chất lượng cuối vẫn phụ thuộc retrieval, evidence và khả năng tuân thủ của model; vì vậy cần RAGAS và phân tích lỗi.

### Tại sao corpus tiếng Anh nhưng hỏi bằng tiếng Việt?

Jina embeddings hỗ trợ semantic retrieval đa ngôn ngữ, nên dense search có thể nối câu hỏi tiếng Việt với tài liệu tiếng Anh. BM25 không tự dịch; đó là lý do nhóm đề xuất query expansion Việt–Anh hoặc bổ sung tóm tắt tiếng Việt.

### Dữ liệu hiện có hạn chế gì?

Corpus chỉ có 9 tài liệu và chưa có Deep Work. Một số bài crawl còn lỗi ký tự hoặc câu bị đứt. Vì vậy hệ thống chủ động từ chối câu ngoài phạm vi và nhóm coi mở rộng, làm sạch corpus là hướng cải thiện quan trọng.

### HyDE đã được dùng chưa?

Chưa được bật trong pipeline hiện tại. Kiến trúc production đang dùng direct query embedding. Nhóm hiểu HyDE và xác định đây là thử nghiệm tiếp theo, nhưng không tuyên bố kết quả chưa chạy.

## 11. Checklist trước khi nộp và demo

Phượng thu xác nhận theo bảng sau:

| Role | Xác nhận bắt buộc |
|---|---|
| Role 2 — Phước | 4 PDF, 5 JSON crawl, 9 Markdown đọc được; metadata có URL |
| Role 3 — Hải | ChromaDB có 229 records; dense search trả kết quả và cosine gốc |
| Role 4 — Mạnh | BM25, RRF, PageIndex registry và test fallback hoạt động |
| Role 5 — Dũng | Streamlit mở được; Task 9/10 READY; câu in-domain có citation |
| Role 6 — Minh Đức | Golden dataset đủ 20 câu; `results.md` chứa kết quả chạy thật hoặc ghi rõ chưa chạy |
| Role 1 — Phượng | Test, README, file trình bày và toàn bộ deliverables đã kiểm tra |

Các lệnh cuối:

```powershell
.\.venv\Scripts\python.exe -m src.supervisor
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## 12. Những điều tuyệt đối không nói sai

- Không nói corpus có Atomic Habits, Deep Work và Thinking, Fast and Slow đầy đủ; hiện **không có Deep Work**.
- Không nói HyDE đã được triển khai hoặc benchmark; code hiện tại chưa có HyDE.
- Không dùng RRF score để giải thích threshold fallback.
- Không đọc điểm RAGAS giả hoặc để trống như thể đó là kết quả thật.
- Không nói PageIndex tìm trên Internet; nó truy hồi trên PDF corpus đã upload.
- Không để lộ `OPENAI_API_KEY`, `JINA_API_KEY` hoặc `PAGEINDEX_API_KEY` trên màn hình demo.
