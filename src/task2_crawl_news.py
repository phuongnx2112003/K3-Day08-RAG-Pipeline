"""
Task 2 — Crawl bài review/phân tích công khai về sách.

Mỗi file JSON giữ URL, thời điểm crawl, metadata sách và phần nội dung bài viết.
Crawler chỉ lấy paragraph của bài để loại menu, footer và điều hướng trang.
"""

import json
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"


def setup_directory():
    """Tạo thư mục data/landing/news/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


ARTICLE_URLS = [
    # Phát triển bản thân - Atomic Habits (James Clear)
    "https://jamesclear.com/atomic-habits-summary",
    "https://jamesclear.com/three-steps-habit-change",
    # Kinh doanh - The Lean Startup (Eric Ries)
    "https://theleanstartup.com/book",
    # Tâm lý học - Thinking, Fast and Slow (Daniel Kahneman)
    "https://en.wikipedia.org/wiki/Thinking,_Fast_and_Slow",
    # Công nghệ - The Innovators (Walter Isaacson)
    "https://en.wikipedia.org/wiki/The_Innovators_(book)",
]

BOOK_METADATA = {
    ARTICLE_URLS[0]: {"book_title": "Atomic Habits", "author": "James Clear", "category": "personal_development"},
    ARTICLE_URLS[1]: {"book_title": "Atomic Habits", "author": "James Clear", "category": "personal_development"},
    ARTICLE_URLS[2]: {"book_title": "The Lean Startup", "author": "Eric Ries", "category": "business"},
    ARTICLE_URLS[3]: {"book_title": "Thinking, Fast and Slow", "author": "Daniel Kahneman", "category": "psychology"},
    ARTICLE_URLS[4]: {"book_title": "The Innovators", "author": "Walter Isaacson", "category": "technology"},
}


class ArticleParser(HTMLParser):
    """Extract visible article paragraphs without navigation labels."""

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._tag: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):  # type: ignore[no-untyped-def]
        if tag in {"title", "p"}:
            self._tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag == self._tag:
            self._tag = None

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self._tag == "title" and not self.title:
            self.title = cleaned
        elif self._tag == "p" and len(cleaned) > 30:
            self._parts.append(cleaned)

    def content(self) -> str:
        return "\n\n".join(self._parts)[:2500]


def crawl_article(url: str) -> dict:
    """
    Crawl một bài viết và trả về dict chứa metadata + content.

    Returns:
        {
            "url": str,
            "title": str,
            "date_crawled": str (ISO format),
            "content_markdown": str
        }
    """
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; C3-02-RAG/1.0)"})
    with urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")
    parser = ArticleParser()
    parser.feed(html)
    content = parser.content()
    if len(content) < 500:
        raise ValueError(f"Extracted content is too short from {url}")
    return {
        "url": url,
        "title": parser.title or "Untitled",
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": content,
        "type": "public_book_article",
        "rights_note": "Short extract from a public webpage; retain source URL.",
        **BOOK_METADATA[url],
    }


def crawl_all():
    """Crawl toàn bộ bài viết trong ARTICLE_URLS."""
    setup_directory()

    for i, url in enumerate(ARTICLE_URLS, 1):
        print(f"[{i}/{len(ARTICLE_URLS)}] Crawling: {url}")
        article = crawl_article(url)

        # Lưu file JSON
        filename = f"article_{i:02d}.json"
        filepath = DATA_DIR / filename
        filepath.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ Saved: {filepath}")


if __name__ == "__main__":
    if not ARTICLE_URLS:
        print("⚠ Hãy điền ARTICLE_URLS trước khi chạy!")
        print("Gợi ý: tìm trang thông báo/sự kiện trên trang chính thức của trường đại học")
    else:
        crawl_all()
