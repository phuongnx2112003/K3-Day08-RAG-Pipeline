import unittest

from src.task4_chunking_indexing import chunk_documents, load_documents
from src.task6_lexical_search import (
    build_bm25_index,
    initialize_indexes,
    lexical_search,
    load_shared_corpus,
)


SAMPLE_CORPUS = [
    {
        "content": "Atomic Habits presents four laws of behavior change.",
        "metadata": {"source": "atomic.md", "chunk_index": 0},
    },
    {
        "content": "Deep Work explains concentration without distraction.",
        "metadata": {"source": "deep-work.md", "chunk_index": 0},
    },
    {
        "content": "System 1 is fast while System 2 is deliberate and slow.",
        "metadata": {"source": "thinking.md", "chunk_index": 0},
    },
]


class TestTask6LexicalSearch(unittest.TestCase):
    def setUp(self):
        initialize_indexes(SAMPLE_CORPUS, include_tfidf=True)

    def test_build_bm25_index(self):
        index = build_bm25_index(SAMPLE_CORPUS)
        self.assertEqual(len(index.doc_len), len(SAMPLE_CORPUS))

    def test_bm25_returns_relevant_chunk_with_shared_contract(self):
        results = lexical_search("four laws behavior change", top_k=2)
        self.assertTrue(results)
        self.assertEqual(results[0]["metadata"]["source"], "atomic.md")
        self.assertEqual(set(results[0]), {"content", "score", "metadata"})
        self.assertGreater(results[0]["score"], 0)

    def test_tfidf_returns_relevant_chunk(self):
        results = lexical_search("System 1 deliberate slow", top_k=2, method="tfidf")
        self.assertTrue(results)
        self.assertEqual(results[0]["metadata"]["source"], "thinking.md")
        self.assertGreater(results[0]["score"], 0)

    def test_scores_are_descending_and_respect_top_k(self):
        results = lexical_search("work system fast", top_k=2)
        self.assertLessEqual(len(results), 2)
        scores = [result["score"] for result in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_empty_query_and_non_positive_top_k_return_empty(self):
        self.assertEqual(lexical_search("   "), [])
        self.assertEqual(lexical_search("atomic", top_k=0), [])

    def test_real_corpus_is_available(self):
        corpus = load_shared_corpus()
        self.assertGreaterEqual(len(corpus), 9)
        self.assertTrue(all("content" in item and "metadata" in item for item in corpus))

    def test_corpus_exactly_matches_task4_chunk_contract(self):
        task4_chunks = chunk_documents(load_documents())
        self.assertEqual(load_shared_corpus(), task4_chunks)


if __name__ == "__main__":
    unittest.main()
