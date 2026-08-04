"""
Task 1 — Tải PDF công khai phục vụ Book Insights RAG.

Chỉ dùng phụ lục, excerpt, book review hoặc tài liệu phân tích được công bố công
khai. Không tải ebook toàn văn có bản quyền. File được lưu tại
data/landing/legal/ để tương thích cấu trúc starter project.
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
    downloads: list[tuple[Path, bytes]] = []
    failures: list[str] = []
    for filename, url in SOURCE_DOCUMENTS:
        path = DATA_DIR / filename
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; C3-02-RAG/1.0)"})
            with urlopen(request, timeout=30) as response:
                content = response.read()
            if not content.startswith(b"%PDF") or len(content) <= 1024:
                raise ValueError("response is not a valid PDF")
        except Exception as exc:
            failures.append(f"{url}: {exc}")
            continue
        downloads.append((path, content))
    if failures:
        raise RuntimeError("Task 1 aborted; no files were updated:\n" + "\n".join(failures))
    for path, content in downloads:
        path.write_bytes(content)
    return [path for path, _ in downloads]


if __name__ == "__main__":
    for path in collect_source_briefs():
        print(f"Ready: {path}")
