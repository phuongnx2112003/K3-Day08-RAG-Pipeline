"""Role 6 evaluation runner: RAGAS when available, reproducible offline proxy otherwise."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
RESULTS_PATH = Path(__file__).parent / "results.md"


def load_golden_dataset() -> list[dict]:
    return json.loads(GOLDEN_DATASET_PATH.read_text(encoding="utf-8"))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE))


def _invoke(pipeline: Any, question: str) -> dict:
    worker = getattr(pipeline, "generate_with_citation", pipeline)
    return worker(question)


def _offline_rows(rag_pipeline: Any, golden_dataset: list[dict], retrieve_kwargs: dict | None = None) -> list[dict]:
    """Deterministic diagnostic metrics; not a substitute for LLM-judged RAGAS."""
    from src.task9_retrieval_pipeline import retrieve
    rows = []
    for item in golden_dataset:
        if retrieve_kwargs is None:
            response = _invoke(rag_pipeline, item["question"])
            answer, sources = response.get("answer", ""), response.get("sources", [])
        else:
            sources = retrieve(item["question"], top_k=5, **retrieve_kwargs)
            answer = " ".join(source.get("content", "") for source in sources)
        context = " ".join(source.get("content", "") for source in sources)
        expected, expected_context = item["expected_answer"], item["expected_context"]
        answer_tokens, context_tokens = _tokens(answer), _tokens(context)
        expected_tokens, target_tokens = _tokens(expected), _tokens(expected_context)
        rows.append({
            "question": item["question"],
            "faithfulness": len(answer_tokens & context_tokens) / max(len(answer_tokens), 1),
            "answer_relevance": len(answer_tokens & expected_tokens) / max(len(expected_tokens), 1),
            "context_recall": len(context_tokens & expected_tokens) / max(len(expected_tokens), 1),
            "context_precision": len(context_tokens & target_tokens) / max(len(context_tokens), 1),
        })
    return rows


def _summary(rows: list[dict]) -> dict[str, float]:
    metrics = ("faithfulness", "answer_relevance", "context_recall", "context_precision")
    return {metric: round(sum(row[metric] for row in rows) / max(len(rows), 1), 4) for metric in metrics}


def evaluate_with_ragas(rag_pipeline: Any, golden_dataset: list[dict]) -> dict:
    """Run the four required RAGAS metrics, or return labelled offline diagnostics."""
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
        records = [_invoke(rag_pipeline, item["question"]) for item in golden_dataset]
        dataset = Dataset.from_dict({
            "question": [item["question"] for item in golden_dataset],
            "answer": [record.get("answer", "") for record in records],
            "contexts": [[source.get("content", "") for source in record.get("sources", [])] for record in records],
            "ground_truth": [item["expected_answer"] for item in golden_dataset],
        })
        scores = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_recall, context_precision])
        return {"framework": "ragas", "scores": {key: float(value) for key, value in scores.items()}}
    except ImportError:
        rows = _offline_rows(rag_pipeline, golden_dataset)
        return {"framework": "offline lexical proxy (install ragas + datasets for LLM judging)", "scores": _summary(rows), "rows": rows}


def compare_configs(rag_pipeline: Any, golden_dataset: list[dict]) -> dict:
    """Compare hybrid+Jina reranking with hybrid retrieval before reranking."""
    configs = {"A_hybrid_jina_rerank": {"use_reranking": True}, "B_hybrid_no_rerank": {"use_reranking": False}}
    return {name: {"scores": _summary(rows := _offline_rows(rag_pipeline, golden_dataset, config)), "rows": rows}
            for name, config in configs.items()}


def export_results(results: dict, comparison: dict) -> None:
    scores = results["scores"]
    lines = ["# RAG Evaluation Results", "", f"Framework: **{results['framework']}**", "",
             "> Offline proxy metrics are lexical diagnostics only. Run `python3 group_project/evaluation/eval_pipeline.py` after installing RAGAS and configuring OpenAI to obtain the required LLM-judged metrics.", "",
             "## Overall Scores", "", "| Metric | Score |", "|---|---:|"]
    lines += [f"| {key.replace('_', ' ').title()} | {value:.4f} |" for key, value in scores.items()]
    lines += ["", "## A/B Comparison", "", "| Metric | A: hybrid + Jina rerank | B: hybrid no rerank | Δ |", "|---|---:|---:|---:|"]
    for metric in scores:
        a, b = comparison["A_hybrid_jina_rerank"]["scores"][metric], comparison["B_hybrid_no_rerank"]["scores"][metric]
        lines.append(f"| {metric.replace('_', ' ').title()} | {a:.4f} | {b:.4f} | {a-b:+.4f} |")
    worst = sorted(results.get("rows", []), key=lambda row: sum(row[key] for key in scores) / len(scores))[:3]
    lines += ["", "## Worst Performers (offline diagnostic)", "", "| Question | Faithfulness | Answer relevance | Context recall | Context precision |", "|---|---:|---:|---:|---:|"]
    lines += [f"| {row['question']} | {row['faithfulness']:.3f} | {row['answer_relevance']:.3f} | {row['context_recall']:.3f} | {row['context_precision']:.3f} |" for row in worst]
    lines += ["", "## Recommendations", "", "1. Run the RAGAS path with a configured OpenAI judge before presentation; record the generated report.", "2. Inspect low-recall questions and add concise, rights-cleared source passages where corpus evidence is absent.", "3. Calibrate the dense threshold using in-domain and out-of-domain queries; PageIndex should remain an optional remote fallback."]
    RESULTS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    from src import task10_generation
    dataset = load_golden_dataset()
    if len(dataset) < 15:
        raise SystemExit("Golden dataset must contain at least 15 cases")
    result = evaluate_with_ragas(task10_generation, dataset)
    comparison = compare_configs(task10_generation, dataset)
    export_results(result, comparison)
    print(f"Wrote {RESULTS_PATH} for {len(dataset)} golden cases")
