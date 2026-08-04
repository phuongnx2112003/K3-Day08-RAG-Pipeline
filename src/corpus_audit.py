"""Audit corpus Markdown trước khi xây BM25 index.

Chạy:
    python -m src.corpus_audit
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .text_normalization import normalize_text, tokenize_bm25


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STANDARDIZED_DIR = PROJECT_ROOT / "data" / "standardized"
REPORT_PATH = PROJECT_ROOT / "group_project" / "checkpoints" / "cp1_role4_corpus_audit.md"

_H1_RE = re.compile(r"^#\s+(.+)$", flags=re.MULTILINE)
_META_RE = re.compile(r"^\*\*([^*]+):\*\*\s*(.+)$", flags=re.MULTILINE)


@dataclass(frozen=True)
class DocumentAudit:
    path: Path
    byte_count: int
    token_count: int
    unique_token_count: int
    form_feed_count: int
    long_line_count: int
    short_fragment_count: int
    missing_metadata: tuple[str, ...]

    @property
    def status(self) -> str:
        return "PASS" if not self.missing_metadata and self.token_count >= 100 else "REVIEW"


def _metadata(text: str) -> dict[str, str]:
    values = {key.strip().lower(): value.strip() for key, value in _META_RE.findall(text)}
    heading = _H1_RE.search(text)
    if heading:
        values["title"] = heading.group(1).strip()
    return values


def audit_document(path: Path) -> DocumentAudit:
    raw = path.read_text(encoding="utf-8", errors="strict")
    metadata = _metadata(raw)
    required = ("title", "source", "type")
    tokens = tokenize_bm25(raw)
    lines = raw.splitlines()
    short_fragments = sum(
        1
        for line in lines
        if line.strip()
        and not line.lstrip().startswith(("#", "**", "---"))
        and len(tokenize_bm25(line)) <= 3
    )
    return DocumentAudit(
        path=path,
        byte_count=path.stat().st_size,
        token_count=len(tokens),
        unique_token_count=len(set(tokens)),
        form_feed_count=raw.count("\f"),
        long_line_count=sum(len(line) > 500 for line in lines),
        short_fragment_count=short_fragments,
        missing_metadata=tuple(key for key in required if not metadata.get(key)),
    )


def audit_corpus(directory: Path = STANDARDIZED_DIR) -> list[DocumentAudit]:
    return [audit_document(path) for path in sorted(directory.rglob("*.md"))]


def render_report(audits: list[DocumentAudit]) -> str:
    total_tokens = sum(item.token_count for item in audits)
    rows = [
        "# Checkpoint 1 — Role 4: BM25 Corpus Audit",
        "",
        "## Kết luận",
        "",
        f"- Số tài liệu Markdown: {len(audits)}",
        f"- Tổng token sau chuẩn hóa: {total_tokens:,}",
        f"- File đủ điều kiện tokenize: {sum(item.status == 'PASS' for item in audits)}/{len(audits)}",
        "- Encoding yêu cầu: UTF-8 strict",
        "- Tokenizer: Unicode NFKC + casefold; giữ dấu tiếng Việt, số và từ ghép",
        "",
        "## Chi tiết",
        "",
        "| File | Tokens | Unique | Form feeds | Dòng >500 | Đoạn ngắn | Metadata | Status |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in audits:
        relative = item.path.relative_to(PROJECT_ROOT).as_posix()
        metadata = ", ".join(item.missing_metadata) if item.missing_metadata else "OK"
        rows.append(
            f"| `{relative}` | {item.token_count} | {item.unique_token_count} | "
            f"{item.form_feed_count} | {item.long_line_count} | "
            f"{item.short_fragment_count} | {metadata} | {item.status} |"
        )

    rows.extend(
        [
            "",
            "## Đề xuất chuẩn hóa",
            "",
            "1. Dùng `src.text_normalization.tokenize_bm25()` cho cả corpus và query.",
            "2. Không bỏ dấu tiếng Việt và không dùng `.split()` trực tiếp.",
            "3. Loại form feed/control, nối từ bị PDF ngắt dòng và gom whitespace khi index.",
            "4. Giữ tiêu đề, tác giả, tên sách và source trong nội dung index để hỗ trợ truy vấn thực thể.",
            "5. Không ghi đè file gốc; chuẩn hóa trong bộ nhớ để citation vẫn trỏ đúng tài liệu bàn giao.",
            "6. Role 2 nên rà lại các bài crawl có nhiều đoạn ngắn vì anchor text có thể đã bị mất.",
            "",
            "## Rủi ro ngôn ngữ",
            "",
            "Corpus hiện chủ yếu là tiếng Anh, trong khi câu hỏi demo dự kiến bằng tiếng Việt. "
            "BM25 không tự dịch truy vấn nên có thể trả tài liệu không liên quan dù dense retrieval "
            "đa ngôn ngữ vẫn tìm đúng. Nên bổ sung bản tóm tắt tiếng Việt hoặc mở rộng truy vấn "
            "Việt-Anh trước bước BM25. Không nên bỏ dấu để giải quyết vấn đề này vì bỏ dấu không "
            "khắc phục được khác biệt ngôn ngữ.",
            "",
            "Các file crawl `article_02.md`, `article_04.md` và `article_05.md` cũng cần Role 2 "
            "đối chiếu URL gốc vì một số anchor text đã bị mất, làm câu bị đứt.",
            "",
            "## Quyết định bàn giao",
            "",
            "Corpus hiện có thể tokenize cho BM25. Các lỗi whitespace/control được xử lý ở lớp "
            "normalization; lỗi thiếu nội dung do crawler cần Role 2 kiểm tra lại từ URL gốc.",
            "",
        ]
    )
    return "\n".join(rows)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if not STANDARDIZED_DIR.exists():
        raise FileNotFoundError(f"Không tìm thấy corpus: {STANDARDIZED_DIR}")

    audits = audit_corpus()
    if not audits:
        raise RuntimeError(f"Không có file Markdown trong {STANDARDIZED_DIR}")

    report = render_report(audits)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
