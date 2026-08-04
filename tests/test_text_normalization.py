from src.text_normalization import normalize_text, tokenize_bm25


def test_normalize_pdf_artifacts_and_html_entities():
    text = "habi-\n  ts\f &amp;  deep\u200b   work"
    assert normalize_text(text) == "habits & deep work"


def test_tokenizer_preserves_vietnamese_and_compound_words():
    assert tokenize_bm25("Thói quen tốt: Deep-Work 1%") == [
        "thói",
        "quen",
        "tốt",
        "deep-work",
        "1",
    ]


def test_tokenizer_casefolds_unicode_text():
    assert tokenize_bm25("ATOMIC Habits") == ["atomic", "habits"]

