import unittest
from unittest.mock import patch

from src.task10_generation import (
    REFUSAL_MESSAGE,
    format_context,
    generate_with_citation,
    prepare_citation_sources,
    reorder_for_llm,
    validate_citations,
)
from src.task9_retrieval_pipeline import retrieve


def chunk(name, index, score, content=None):
    return {
        "content": content or f"{name} content {index}",
        "score": score,
        "metadata": {"source": name, "type": "news", "chunk_index": index},
    }


class TestTask9Integration(unittest.TestCase):
    @patch("src.task9_retrieval_pipeline.pageindex_search")
    @patch("src.task9_retrieval_pipeline.lexical_search")
    @patch("src.task9_retrieval_pipeline.semantic_search")
    def test_hybrid_rrf_contract(self, semantic, lexical, pageindex):
        semantic.return_value = [chunk("atomic.md", 0, 0.7), chunk("deep.md", 0, 0.6)]
        lexical.return_value = [chunk("atomic.md", 0, 12.0), chunk("lean.md", 0, 8.0)]

        results = retrieve("atomic habits", top_k=3, score_threshold=0.4)

        pageindex.assert_not_called()
        self.assertEqual(results[0]["metadata"]["source"], "atomic.md")
        self.assertEqual(results[0]["source"], "hybrid")
        self.assertEqual(set(results[0]) & {"content", "score", "metadata", "source"},
                         {"content", "score", "metadata", "source"})

    @patch("src.task9_retrieval_pipeline.pageindex_search")
    @patch("src.task9_retrieval_pipeline.lexical_search", return_value=[])
    @patch("src.task9_retrieval_pipeline.semantic_search")
    def test_low_raw_dense_score_triggers_pageindex(self, semantic, _lexical, pageindex):
        semantic.return_value = [chunk("atomic.md", 0, 0.18)]
        pageindex.return_value = [{
            "content": "PageIndex evidence",
            "score": 1.0,
            "metadata": {"section": "Atomic"},
            "source": "pageindex",
        }]

        results = retrieve("outside domain", top_k=2, score_threshold=0.4)

        pageindex.assert_called_once()
        self.assertEqual(results[0]["source"], "pageindex")

    @patch("src.task9_retrieval_pipeline.pageindex_search", return_value=[])
    @patch("src.task9_retrieval_pipeline.lexical_search", return_value=[])
    @patch("src.task9_retrieval_pipeline.semantic_search")
    def test_no_fallback_evidence_returns_empty(self, semantic, _lexical, _pageindex):
        semantic.return_value = [chunk("atomic.md", 0, 0.1)]
        self.assertEqual(retrieve("bitcoin price", score_threshold=0.4), [])

    @patch("src.task9_retrieval_pipeline.semantic_search")
    def test_dense_only_can_disable_fallback(self, semantic):
        semantic.return_value = [chunk("atomic.md", 0, 0.2)]
        results = retrieve(
            "benchmark query",
            top_k=1,
            retrieval_mode="dense_only",
            use_pageindex_fallback=False,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"]["retrieval_mode"], "dense_only")


class TestTask10Generation(unittest.TestCase):
    def test_reorder_and_context_labels(self):
        chunks = [chunk("book.md", index, 1 - index / 10) for index in range(5)]
        reordered = reorder_for_llm(chunks)
        self.assertEqual([item["metadata"]["chunk_index"] for item in reordered], [0, 2, 4, 3, 1])

        sources = prepare_citation_sources(reordered)
        context = format_context(sources)
        self.assertIn("[S1]", context)
        self.assertIn("book.md", context)

    def test_citation_validation(self):
        self.assertEqual(validate_citations("Claim [S1].", 2), (True, []))
        self.assertEqual(validate_citations("Claim [S9].", 2), (False, ["S9"]))
        self.assertEqual(validate_citations(REFUSAL_MESSAGE, 0), (True, []))

    @patch("src.task10_generation.retrieve", return_value=[])
    def test_empty_evidence_refuses_without_llm(self, _retrieve):
        result = generate_with_citation("Giá Bitcoin hôm nay?")
        self.assertEqual(result["answer"], REFUSAL_MESSAGE)
        self.assertEqual(result["sources"], [])

    @patch("src.task10_generation._openai_answer", return_value="Có bốn quy luật [S1].")
    @patch("src.task10_generation.retrieve")
    def test_generation_returns_citations_and_sources(self, mocked_retrieve, mocked_openai):
        mocked_retrieve.return_value = [chunk("atomic.md", 3, 0.03, "Four laws")]
        result = generate_with_citation("Bốn quy luật là gì?")

        mocked_openai.assert_called_once()
        self.assertTrue(result["citations_valid"])
        self.assertEqual(result["sources"][0]["metadata"]["citation_id"], "S1")
        self.assertEqual(result["retrieval_source"], "hybrid")


if __name__ == "__main__":
    unittest.main()
