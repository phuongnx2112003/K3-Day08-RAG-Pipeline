"""
Task 3 — Convert toàn bộ file trong data/landing/ thành Markdown.

Sử dụng MarkItDown của Microsoft:
    https://github.com/microsoft/markitdown

Cài đặt:
    pip install "markitdown[pdf]"
    # Lưu ý: cần extra [pdf] để convert được file PDF. Chỉ "pip install markitdown"
    # (không có extra) sẽ báo MissingDependencyException khi convert PDF, dù JSON/DOCX
    # vẫn convert bình thường.

Hướng dẫn:
    1. Scan toàn bộ file trong data/landing/ (PDF, DOCX, JSON)
    2. Convert sang Markdown
    3. Lưu vào data/standardized/ giữ nguyên cấu trúc thư mục
"""

import json
import subprocess
import zipfile
from xml.etree import ElementTree
from pathlib import Path

try:
    from markitdown import MarkItDown
except ImportError:
    MarkItDown = None

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

PDF_METADATA = {
    "atomic-habits-business-appendix.pdf": ("Atomic Habits", "James Clear", "personal_development", "https://s3.amazonaws.com/jamesclear/Atomic%20Habits/Business%20Appendix.pdf"),
    "thinking-fast-slow-cia-review.pdf": ("Thinking, Fast and Slow", "Daniel Kahneman", "psychology", "https://www.cia.gov/resources/csi/static/Thinking-Fast-and-Slow.pdf"),
    "thinking-fast-slow-innovation-review.pdf": ("Thinking, Fast and Slow", "Daniel Kahneman", "psychology", "https://innovation.cc/wp-content/uploads/2012_17_3_10_gow_bk_rev_kahneman.pdf"),
    "lean-startup-method-analysis.pdf": ("The Lean Startup", "Eric Ries", "business", "https://assets.website-files.com/6754fde9083ed68513741b0b/681768721e7e0d62338789a2_51868898252.pdf"),
}


def _extract_docx_text(filepath: Path) -> str:
    with zipfile.ZipFile(filepath) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    return "\n".join(node.text or "" for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))


def convert_legal_docs():
    """Convert PDF/DOCX files trong data/landing/legal/ sang markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    md = MarkItDown() if MarkItDown else None

    for filepath in legal_dir.iterdir():
        if filepath.suffix.lower() in (".pdf", ".docx", ".doc"):
            print(f"Converting: {filepath.name}")
            if md:
                text = md.convert(str(filepath)).text_content
            elif filepath.suffix.lower() == ".pdf":
                text = subprocess.run(["pdftotext", str(filepath), "-"], check=True, capture_output=True, text=True).stdout
            elif filepath.suffix.lower() == ".docx":
                text = _extract_docx_text(filepath)
            else:
                raise ValueError(".doc requires MarkItDown; convert it to .docx or install MarkItDown.")
            output_path = output_dir / f"{filepath.stem}.md"
            title, author, category, source_url = PDF_METADATA.get(filepath.name, (filepath.stem, "Unknown", "unknown", "N/A"))
            header = f"# {title}\n\n**Author:** {author}\n**Category:** {category}\n**Source:** {source_url}\n**Type:** public_pdf\n\n---\n\n"
            output_path.write_text(header + text, encoding="utf-8")
            print(f"  ✓ Saved: {output_path}")


def convert_news_articles():
    """Convert JSON crawled articles trong data/landing/news/ sang markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for filepath in news_dir.iterdir():
        if filepath.suffix.lower() == ".json":
            print(f"Converting: {filepath.name}")
            data = json.loads(filepath.read_text(encoding="utf-8"))
            output_path = output_dir / f"{filepath.stem}.md"
            header = f"# {data.get('title', 'Unknown')}\n\n"
            header += f"**Source:** {data.get('url', 'N/A')}\n"
            header += f"**Crawled:** {data.get('date_crawled', 'N/A')}\n"
            header += f"**Book:** {data.get('book_title', 'Unknown')}\n"
            header += f"**Author:** {data.get('author', 'Unknown')}\n"
            header += f"**Category:** {data.get('category', 'unknown')}\n"
            header += f"**Type:** {data.get('type', 'public_book_article')}\n\n---\n\n"
            output_path.write_text(header + data.get("content_markdown", ""), encoding="utf-8")
            print(f"  ✓ Saved: {output_path}")


def convert_all():
    """Convert toàn bộ files."""
    print("=" * 50)
    print("Task 3: Convert to Markdown (MarkItDown)")
    print("=" * 50)

    print("\n--- Legal Documents ---")
    convert_legal_docs()

    print("\n--- News Articles ---")
    convert_news_articles()

    print("\n✓ Done! Output tại:", OUTPUT_DIR)


if __name__ == "__main__":
    convert_all()
