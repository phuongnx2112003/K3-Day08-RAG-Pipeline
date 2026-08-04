"""Contract tests for the Role 1 supervisor layer."""

import unittest

from src.supervisor import PipelineSupervisor


class TestPipelineSupervisor(unittest.TestCase):
    def test_retrieve_evidence_delegates_to_retrieval_worker(self):
        def retriever(query, top_k):
            self.assertEqual(query, "Học phí là bao nhiêu?")
            self.assertEqual(top_k, 2)
            return [{"content": "Tuition information", "score": 0.9, "metadata": {}}]

        supervisor = PipelineSupervisor(retriever=retriever)
        results = supervisor.retrieve_evidence("Học phí là bao nhiêu?", top_k=2)
        self.assertEqual(len(results), 1)

    def test_answer_normalizes_generation_response(self):
        def generator(query, top_k):
            return {
                "answer": "Thông tin học phí [Tuition 2026]",
                "sources": [{"content": "...", "metadata": {}}],
                "retrieval_source": "hybrid",
            }

        response = PipelineSupervisor(generator=generator).answer("Học phí?", top_k=3)
        self.assertEqual(response["retrieval_source"], "hybrid")
        self.assertEqual(len(response["sources"]), 1)

    def test_empty_query_is_rejected(self):
        supervisor = PipelineSupervisor(retriever=lambda *_args, **_kwargs: [])
        with self.assertRaises(ValueError):
            supervisor.retrieve_evidence("   ")

    def test_health_check_marks_injected_workers_ready(self):
        supervisor = PipelineSupervisor(
            retriever=lambda *_args, **_kwargs: [],
            generator=lambda *_args, **_kwargs: {"answer": "ok", "sources": []},
        )
        self.assertTrue(all(check.ready for check in supervisor.health_check()))


if __name__ == "__main__":
    unittest.main()
