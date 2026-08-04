"""
Task 1 — Thu thập source brief cho Book Insights RAG.

Hướng dẫn:
    1. Tìm tối thiểu 3 văn bản chính sách (PDF/DOCX) từ trang công khai của một trường đại học.
    2. Tải về và lưu vào data/landing/legal/
    3. Đặt tên file rõ ràng, không dấu, mô tả đúng nội dung.

Gợi ý nguồn (ví dụ trang công khai RMIT Vietnam — rmit.edu.vn):
    - https://www.rmit.edu.vn/study-at-rmit/tuition-fees
    - https://www.rmit.edu.vn/study-at-rmit/scholarships/...
    - https://www.rmit.edu.vn/students/my-studies/fees-and-payments

Gợi ý văn bản (chủ đề dịch vụ đại học):
    - Học phí & phương thức thanh toán (Tuition Fees)
    - Chính sách học bổng (Scholarship eligibility)
    - Quy định ký túc xá / hỗ trợ chỗ ở (Accommodation Services)
    - Hướng dẫn đăng ký học phần qua cổng thông tin sinh viên (Course Registration)

Lưu ý: một số trang trường (vd VinUni, Fulbright) chặn bot crawler mặc định (HTTP 403) —
không phải lỗi của bạn, đó là cấu hình WAF/Cloudflare phía server. Đổi sang trang khác
thay vì cố vượt qua, và chỉ dùng nguồn công khai/được phép chia sẻ.
"""

from pathlib import Path
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


SOURCE_DOCUMENTS = [
    ("atomic-habits-business-appendix.pdf", "https://s3.amazonaws.com/jamesclear/Atomic%20Habits/Business%20Appendix.pdf"),
    ("thinking-fast-slow-cia-review.pdf", "https://www.cia.gov/resources/csi/static/Thinking-Fast-and-Slow.pdf"),
    ("thinking-fast-slow-innovation-review.pdf", "https://innovation.cc/wp-content/uploads/2012_17_3_10_gow_bk_rev_kahneman.pdf"),
    ("lean-startup-method-analysis.pdf", "https://assets.website-files.com/6754fde9083ed68513741b0b/681768721e7e0d62338789a2_51868898252.pdf"),
]


def setup_directory():
    """Tạo thư mục data/landing/legal/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Thư mục đã sẵn sàng: {DATA_DIR}")


def collect_source_briefs() -> list[Path]:
    """Download three publicly shared book-related PDFs with provenance."""
    setup_directory()
    paths = []
    for filename, url in SOURCE_DOCUMENTS:
        path = DATA_DIR / filename
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; C3-02-RAG/1.0)"})
        with urlopen(request, timeout=30) as response:
            content = response.read()
        if not content.startswith(b"%PDF") or len(content) <= 1024:
            raise ValueError(f"Invalid PDF response from {url}")
        path.write_bytes(content)
        paths.append(path)
    return paths


if __name__ == "__main__":
    for path in collect_source_briefs():
        print(f"Ready: {path}")
