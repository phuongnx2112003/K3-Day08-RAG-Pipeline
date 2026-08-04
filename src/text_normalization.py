"""Chuẩn hóa văn bản và tokenize Unicode cho sparse retrieval/BM25."""

from __future__ import annotations

import html
import re
import unicodedata


_ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200d\ufeff]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_DEHYPHENATE_RE = re.compile(r"(?<=\w)-[ \t]*\r?\n[ \t]*(?=\w)")
_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[^\W_]+(?:[’'\-][^\W_]+)*", flags=re.UNICODE)


def normalize_text(text: str) -> str:
    """Trả văn bản ổn định cho BM25 mà không làm mất dấu tiếng Việt.

    Các bước gồm giải mã HTML entity, Unicode NFKC, bỏ ký tự zero-width/control,
    nối từ bị ngắt dòng bởi PDF và gom mọi whitespace về một dấu cách.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    normalized = html.unescape(text)
    normalized = unicodedata.normalize("NFKC", normalized)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _DEHYPHENATE_RE.sub("", normalized)
    normalized = _ZERO_WIDTH_RE.sub("", normalized)
    normalized = _CONTROL_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()


def tokenize_bm25(text: str) -> list[str]:
    """Tokenize không phụ thuộc ngôn ngữ, giữ số, dấu tiếng Việt và từ ghép."""

    normalized = normalize_text(text).casefold()
    return _TOKEN_RE.findall(normalized)

