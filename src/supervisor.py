"""Supervisor layer for the University Services RAG chatbot.

This module belongs to Role 1.  It does not reimplement the retrieval workers;
instead it provides one stable contract for the UI, demo, and evaluation code:

    UI / evaluation -> PipelineSupervisor -> Task 10 -> Task 9 -> retrieval workers

Imports of unfinished worker modules are intentionally lazy.  This lets each
member develop independently while the supervisor can still report which part
of the pipeline is not ready for a demo.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
import inspect
from typing import Any


DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class PipelineHealth:
    """Availability of an integration point needed by the final demo."""

    component: str
    ready: bool
    detail: str


class PipelineSupervisor:
    """Coordinate the retrieval and generation workers through stable methods."""

    def __init__(
        self,
        retriever: Callable[..., list[dict[str, Any]]] | None = None,
        generator: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self._retriever = retriever
        self._generator = generator

    @staticmethod
    def _load_worker(module_name: str, function_name: str) -> Callable[..., Any]:
        """Load a worker only when it is used, so partial team work is safe."""
        module = import_module(module_name)
        worker = getattr(module, function_name)
        if not callable(worker):
            raise TypeError(f"{module_name}.{function_name} must be callable")
        return worker

    def retrieve_evidence(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
        """Delegate evidence retrieval to Task 9 and validate its public contract."""
        self._validate_query(query)
        worker = self._retriever or self._load_worker(
            "src.task9_retrieval_pipeline", "retrieve"
        )
        results = worker(query, top_k=top_k)
        if not isinstance(results, list):
            raise TypeError("Retrieval worker must return list[dict]")
        return results

    def answer(self, query: str, top_k: int = DEFAULT_TOP_K) -> dict[str, Any]:
        """Run the end-to-end RAG path and return a UI-friendly response object."""
        self._validate_query(query)
        worker = self._generator or self._load_worker(
            "src.task10_generation", "generate_with_citation"
        )
        response = worker(query, top_k=top_k)
        if not isinstance(response, dict):
            raise TypeError("Generation worker must return a dictionary")

        answer = response.get("answer")
        if not isinstance(answer, str):
            raise ValueError("Generation response must contain a string 'answer'")

        sources = response.get("sources", [])
        if not isinstance(sources, list):
            raise ValueError("Generation response field 'sources' must be a list")

        return {
            "answer": answer,
            "sources": sources,
            "retrieval_source": response.get("retrieval_source", "none"),
        }

    def health_check(self) -> list[PipelineHealth]:
        """Report readiness without requiring API keys or executing a query."""
        checks = [
            (
                "retrieval pipeline (Task 9)",
                "src.task9_retrieval_pipeline",
                "retrieve",
                self._retriever,
            ),
            (
                "citation generation (Task 10)",
                "src.task10_generation",
                "generate_with_citation",
                self._generator,
            ),
        ]
        report: list[PipelineHealth] = []
        for component, module_name, function_name, injected_worker in checks:
            try:
                worker = injected_worker or self._load_worker(module_name, function_name)
                if injected_worker:
                    report.append(PipelineHealth(component, True, "Worker injected for testing"))
                elif "raise NotImplementedError" in inspect.getsource(worker):
                    report.append(PipelineHealth(component, False, "Worker is still a TODO template"))
                else:
                    report.append(PipelineHealth(component, True, "Worker contract is available"))
            except Exception as exc:  # Show the blocker in the demo checklist.
                report.append(PipelineHealth(component, False, str(exc)))
        return report

    @staticmethod
    def _validate_query(query: str) -> None:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string")


def get_demo_readiness() -> list[PipelineHealth]:
    """Convenience entry point for a pre-demo terminal check."""
    return PipelineSupervisor().health_check()


if __name__ == "__main__":
    for check in get_demo_readiness():
        status = "READY" if check.ready else "BLOCKED"
        print(f"[{status}] {check.component}: {check.detail}")
