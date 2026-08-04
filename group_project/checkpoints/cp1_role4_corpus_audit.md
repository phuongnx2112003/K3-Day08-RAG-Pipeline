# Checkpoint 1 — Role 4: BM25 Corpus Audit

## Kết luận

- Số tài liệu Markdown: 9
- Tổng token sau chuẩn hóa: 21,777
- File đủ điều kiện tokenize: 9/9
- Encoding yêu cầu: UTF-8 strict
- Tokenizer: Unicode NFKC + casefold; giữ dấu tiếng Việt, số và từ ghép

## Chi tiết

| File | Tokens | Unique | Form feeds | Dòng >500 | Đoạn ngắn | Metadata | Status |
|---|---:|---:|---:|---:|---:|---|---|
| `data/standardized/legal/atomic-habits-business-appendix.md` | 7494 | 1740 | 19 | 0 | 73 | OK | PASS |
| `data/standardized/legal/lean-startup-method-analysis.md` | 8206 | 2362 | 11 | 1 | 1 | OK | PASS |
| `data/standardized/legal/thinking-fast-slow-cia-review.md` | 2427 | 915 | 4 | 0 | 13 | OK | PASS |
| `data/standardized/legal/thinking-fast-slow-innovation-review.md` | 1606 | 730 | 3 | 0 | 6 | OK | PASS |
| `data/standardized/news/article_01.md` | 462 | 227 | 0 | 1 | 1 | OK | PASS |
| `data/standardized/news/article_02.md` | 475 | 235 | 0 | 2 | 0 | OK | PASS |
| `data/standardized/news/article_03.md` | 420 | 233 | 0 | 0 | 0 | OK | PASS |
| `data/standardized/news/article_04.md` | 418 | 254 | 0 | 1 | 0 | OK | PASS |
| `data/standardized/news/article_05.md` | 269 | 167 | 0 | 1 | 0 | OK | PASS |

## Đề xuất chuẩn hóa

1. Dùng `src.text_normalization.tokenize_bm25()` cho cả corpus và query.
2. Không bỏ dấu tiếng Việt và không dùng `.split()` trực tiếp.
3. Loại form feed/control, nối từ bị PDF ngắt dòng và gom whitespace khi index.
4. Giữ tiêu đề, tác giả, tên sách và source trong nội dung index để hỗ trợ truy vấn thực thể.
5. Không ghi đè file gốc; chuẩn hóa trong bộ nhớ để citation vẫn trỏ đúng tài liệu bàn giao.
6. Role 2 nên rà lại các bài crawl có nhiều đoạn ngắn vì anchor text có thể đã bị mất.

## Rủi ro ngôn ngữ

Corpus hiện chủ yếu là tiếng Anh, trong khi câu hỏi demo dự kiến bằng tiếng Việt. BM25 không tự dịch truy vấn nên có thể trả tài liệu không liên quan dù dense retrieval đa ngôn ngữ vẫn tìm đúng. Nên bổ sung bản tóm tắt tiếng Việt hoặc mở rộng truy vấn Việt-Anh trước bước BM25. Không nên bỏ dấu để giải quyết vấn đề này vì bỏ dấu không khắc phục được khác biệt ngôn ngữ.

Các file crawl `article_02.md`, `article_04.md` và `article_05.md` cũng cần Role 2 đối chiếu URL gốc vì một số anchor text đã bị mất, làm câu bị đứt.

## Quyết định bàn giao

Corpus hiện có thể tokenize cho BM25. Các lỗi whitespace/control được xử lý ở lớp normalization; lỗi thiếu nội dung do crawler cần Role 2 kiểm tra lại từ URL gốc.
