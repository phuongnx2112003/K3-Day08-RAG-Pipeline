"""Pre-retrieval query normalisation and lightweight Vietnamese-to-corpus expansion.

The indexed sources are primarily English while the chatbot is Vietnamese.  This
module deliberately uses transparent rules rather than an extra LLM request: it
keeps retrieval fast, inexpensive, and easy to explain during the demo.
"""

from __future__ import annotations

import re
import unicodedata

MAX_QUERY_VARIANTS = 4

# Each tuple maps user wording to high-signal vocabulary occurring in the corpus.
DOMAIN_EXPANSIONS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("thói quen", "habit", "atomic"), "atomic habits cue craving response reward four laws behavior change"),
    (("mvp", "lean startup", "khởi nghiệp tinh gọn", "build measure learn", "xây đo học"),
     "lean startup minimum viable product MVP validated learning build measure learn pivot persevere"),
    (("hệ thống 1", "system 1", "hệ thống 2", "system 2", "kahneman", "ra quyết định"),
     "thinking fast slow Kahneman system 1 intuitive emotional system 2 deliberate logical bias"),
    (("đổi mới", "innovator", "công nghệ", "walter isaacson"),
     "the innovators Walter Isaacson digital revolution technology computer innovation"),
)


def normalize_query(query: str) -> str:
    """Collapse spacing and strip control characters without losing Vietnamese accents."""
    normalized = unicodedata.normalize("NFC", query)
    return re.sub(r"\s+", " ", normalized).strip()


def expand_query(query: str, max_variants: int = MAX_QUERY_VARIANTS) -> list[str]:
    """Return the original query plus relevant corpus vocabulary, deduplicated."""
    original = normalize_query(query)
    if not original:
        return []
    searchable = original.casefold()
    variants = [original]
    for triggers, expansion in DOMAIN_EXPANSIONS:
        if any(trigger in searchable for trigger in triggers):
            variants.append(f"{original} {expansion}")
    # A keyword-only pass helps BM25 when an otherwise natural Vietnamese question
    # has no direct English token overlap with the source documents.
    variants.extend(expansion for triggers, expansion in DOMAIN_EXPANSIONS if any(trigger in searchable for trigger in triggers))
    return list(dict.fromkeys(variants))[:max_variants]
