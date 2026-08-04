import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.task7_reranking import rerank, rerank_rrf
from src.task8_pageindex_vectorless import (
    get_registered_doc_ids,
    pageindex_search,
    parse_retrieval_results,
    should_fallback,
)


class TestRRF(unittest.TestCase):
    def setUp(self):
        self.shared_dense = {
            "content": "Atomic Habits four laws",
            "score": 0.72,
            "metadata": {"source": "atomic.md", "type": "news", "chunk_index": 1},
        }
        self.shared_sparse = {
            "content": "Atomic Habits four laws",
            "score": 14.2,
            "metadata": {"source": "atomic.md", "type": "news", "chunk_index": 1},
        }

    def test_shared_chunk_receives_contributions_from_both_rankers(self):
        dense = [self.shared_dense, {"content": "Deep Work", "score": 0.6, "metadata": {}}]
        sparse = [self.shared_sparse, {"content": "Lean Startup", "score": 8.0, "metadata": {}}]
        results = rerank_rrf([dense, sparse], top_k=3, k=60)

        self.assertEqual(results[0]["metadata"]["source"], "atomic.md")
        self.assertAlmostEqual(results[0]["score"], 2 / 61, places=8)
        self.assertEqual(len(results[0]["metadata"]["rrf_evidence"]), 2)

    def test_duplicate_in_one_ranker_only_contributes_once(self):
        results = rerank_rrf(
            [[self.shared_dense, self.shared_dense], [self.shared_sparse]],
            top_k=1,
            k=60,
        )
        self.assertAlmostEqual(results[0]["score"], 2 / 61, places=8)

    def test_single_list_rerank_preserves_rank_order(self):
        candidates = [
            {"content": "A", "score": 10.0, "metadata": {}},
            {"content": "B", "score": 1.0, "metadata": {}},
        ]
        results = rerank("query", candidates, top_k=2, method="rrf")
        self.assertEqual([item["content"] for item in results], ["A", "B"])


class TestPageIndexFallback(unittest.TestCase):
    def test_parse_nested_retrieval_schema(self):
        payload = {
            "id": "retrieval-1",
            "status": "completed",
            "retrieved_nodes": [
                {
                    "node_id": "node-1",
                    "relevant_contents": [
                        [
                            {
                                "section_title": "Four Laws",
                                "relevant_content": "Make it obvious and attractive.",
                            },
                            {
                                "section_title": "Four Laws",
                                "relevant_content": "Make it easy and satisfying.",
                            },
                        ]
                    ],
                }
            ],
        }
        results = parse_retrieval_results(payload, doc_id="doc-1", top_k=5)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["source"], "pageindex")
        self.assertEqual(results[0]["metadata"]["section"], "Four Laws")
        self.assertEqual(results[0]["metadata"]["doc_id"], "doc-1")
        self.assertGreater(results[0]["score"], results[1]["score"])

    def test_no_registry_returns_empty_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "missing.json"
            with patch("src.task8_pageindex_vectorless.REGISTRY_PATH", registry):
                self.assertEqual(get_registered_doc_ids(), [])
                self.assertEqual(pageindex_search("outside domain", top_k=2), [])

    def test_fallback_uses_dense_score_not_rrf_score(self):
        self.assertFalse(should_fallback([{"score": 0.67}], score_threshold=0.4))
        self.assertTrue(should_fallback([{"score": 0.21}], score_threshold=0.4))
        self.assertTrue(should_fallback([], score_threshold=0.4))


if __name__ == "__main__":
    unittest.main()
