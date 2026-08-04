"""
Task 2 — Crawl bài viết/thông báo.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"


def setup_directory():
    """Tạo thư mục data/landing/news/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


ARTICLE_URLS = [
    "https://vi.wikipedia.org/wiki/Th%C3%B3i_quen_nguy%C3%AAn_t%E1%BB%AD",
    "https://vi.wikipedia.org/wiki/T%C6%B0_duy_nhanh_v%C3%A0_ch%E1%BA%ADm",
    "https://vi.wikipedia.org/wiki/%C4%90%E1%BA%AFc_nh%C3%A2n_t%C3%A2m",
    "https://vi.wikipedia.org/wiki/Cha_gi%C3%A0u,_cha_ngh%C3%A8o",
    "https://vi.wikipedia.org/wiki/Nh%C3%A0_gi%E1%BA%A3_kim_(s%C3%A1ch)",
    "https://en.wikipedia.org/wiki/Deep_Work",
]


async def crawl_article(url: str) -> dict:
    """
    Crawl một bài viết và trả về dict chứa metadata + content.
    """
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)

        # Một số version crawl4ai trả markdown dạng object (result.markdown.raw_markdown)
        # thay vì string thuần — xử lý cả 2 trường hợp cho an toàn
        md = result.markdown
        content = getattr(md, "raw_markdown", md) if md else ""

        title = "Unknown"
        if result.metadata:
            title = result.metadata.get("title", "Unknown")

        return {
            "url": url,
            "title": title,
            "date_crawled": datetime.now().isoformat(),
            "content": content,
        }


async def crawl_all():
    """Crawl toàn bộ bài viết trong ARTICLE_URLS."""
    setup_directory()

    for i, url in enumerate(ARTICLE_URLS, 1):
        print(f"[{i}/{len(ARTICLE_URLS)}] Crawling: {url}")
        try:
            article = await crawl_article(url)
        except Exception as e:
            print(f"  ✗ Lỗi khi crawl {url}: {e}")
            continue

        filename = f"article_{i:02d}.json"
        filepath = DATA_DIR / filename
        filepath.write_text(
            json.dumps(article, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"  ✓ Saved: {filepath}")

        # Nghỉ giữa các request để crawl lịch sự (tránh bị chặn)
        await asyncio.sleep(1)


if __name__ == "__main__":
    if not ARTICLE_URLS:
        print("⚠ Hãy điền ARTICLE_URLS trước khi chạy!")
    else:
        asyncio.run(crawl_all())