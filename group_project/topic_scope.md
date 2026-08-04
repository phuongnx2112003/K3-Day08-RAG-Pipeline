# Phạm Vi Đề Tài - Trợ Lý Review & Tóm Tắt Sách Chuyên Sâu

## Mục Tiêu

Chatbot trả lời bằng tiếng Việt về tri thức cốt lõi, bài học thực hành và góc nhìn được nêu trong các tài liệu phân tích sách. Phạm vi ban đầu gồm bốn nhóm: phát triển bản thân, kinh doanh, tâm lý học và công nghệ.

Các đầu sách khởi đầu:

- *Atomic Habits* - James Clear
- *Deep Work* - Cal Newport
- *Thinking, Fast and Slow* - Daniel Kahneman

## Nguồn Dữ Liệu Hợp Lệ

Chỉ đưa vào repository các nguồn sau:

- Bản tóm tắt hoặc ghi chú do thành viên nhóm tự viết.
- Bài review/phân tích công khai, giữ URL gốc và ngày crawl.
- Đoạn trích ngắn được người dùng/giảng viên cung cấp hoặc nguồn cho phép sử dụng.
- Trang chính thức của tác giả/nhà xuất bản mô tả nội dung sách.

Không tải, crawl hoặc commit ebook/PDF toàn văn có bản quyền khi nhóm không có quyền sử dụng. Chatbot phải trả lời từ context đã index, không tái tạo nội dung dài của sách.

## Quy Ước Thư Mục

Tên thư mục `legal` và `news` được giữ lại do starter test yêu cầu; trong đề tài này chúng có ý nghĩa:

| Đường dẫn | Nội dung |
|---|---|
| `data/landing/legal/` | Bản tóm tắt, ghi chú hoặc tài liệu phân tích sách hợp lệ |
| `data/landing/news/` | Bài review/phân tích công khai có URL nguồn |
| `data/standardized/legal/` | Markdown đã chuẩn hóa từ tài liệu sách |
| `data/standardized/news/` | Markdown đã chuẩn hóa từ review/bài phân tích |

## Metadata Bắt Buộc

Mỗi document hoặc chunk phải có tối thiểu các trường sau:

```json
{
  "source": "atomic-habits-summary.md",
  "type": "book_summary",
  "book_title": "Atomic Habits",
  "author": "James Clear",
  "category": "personal_development",
  "source_url": "https://...",
  "rights_note": "team-written-summary"
}
```

`source_url` có thể để trống cho ghi chú tự viết; `rights_note` vẫn bắt buộc để mô tả nguồn và quyền sử dụng.

## Tiêu Chí Cho Golden Dataset

Role 6 thay thế toàn bộ câu hỏi RMIT hiện có bằng tối thiểu 20 câu hỏi dựa trên chính corpus đã index. Dataset cần có câu hỏi về tóm tắt, khái niệm, so sánh và câu hỏi ngoài phạm vi để kiểm thử fallback. `expected_context` phải chỉ đúng tên sách/tài liệu và phần chứa evidence.
