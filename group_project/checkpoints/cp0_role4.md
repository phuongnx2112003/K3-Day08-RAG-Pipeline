# Checkpoint 0 — Role 4: Sparse Retrieval & Fallback

## Trạng thái

- Python: 3.10.11
- Môi trường ảo: `.venv`
- `rank-bm25`: 0.2.2 — đã cài đặt và kiểm tra import
- `pageindex`: 0.2.8 — đã cài đặt và kiểm tra import
- `OPENAI_API_KEY`: đã cấu hình cục bộ, dùng làm LLM provider
- `PAGEINDEX_API_KEY`: đã cấu hình cục bộ, sẵn sàng cho PageIndex Cloud

## Kết luận bàn giao

Môi trường cho BM25 đã sẵn sàng để triển khai Task 6. SDK và API key của PageIndex
đã được cấu hình để chuẩn bị cho Task 8. Nhóm sử dụng OpenAI làm LLM provider;
không phụ thuộc `OPENROUTER_API_KEY`.

Không lưu API key trong repository. Các khóa chỉ được khai báo cục bộ trong `.env`:

```dotenv
OPENAI_API_KEY=your_openai_api_key
PAGEINDEX_API_KEY=your_pageindex_api_key
```

## Lệnh xác minh

```powershell
.\.venv\Scripts\python.exe -c "from rank_bm25 import BM25Okapi; print('rank-bm25 OK')"
.\.venv\Scripts\python.exe -c "import pageindex; print('pageindex OK')"
```
