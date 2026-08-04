"""
RAG Evaluation Pipeline (A/B) cho bài nhóm.

Mục tiêu của script này là tạo `group_project/evaluation/results.md` từ kết quả chạy THẬT.

Lưu ý quan trọng:
- Script này KHÔNG hard-code số liệu.
- Nếu thiếu API key / bị chặn mạng khiến retrieval/generation không chạy được, script vẫn chạy
  nhưng sẽ phản ánh đúng tình trạng (ví dụ nhiều câu bị từ chối, ít sources, ...).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Windows console UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

EVAL_DIR = Path(__file__).resolve().parent
GOLDEN_DATASET_PATH = EVAL_DIR / "golden_dataset.json"
RESULTS_MD_PATH = EVAL_DIR / "results.md"
DEFAULT_OUTPUT_PATH = EVAL_DIR / "results.generated.md"


REFUSAL_MESSAGE = "Tôi không thể xác minh thông tin này từ nguồn hiện có."
DEFAULT_JUDGE_MODEL = os.getenv("RAGAS_JUDGE_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
DEFAULT_EMBED_MODEL = os.getenv("RAGAS_EMBEDDING_MODEL", "text-embedding-3-small")


def load_golden_dataset() -> list[dict[str, Any]]:
    return json.loads(GOLDEN_DATASET_PATH.read_text(encoding="utf-8"))


def require_openai_key() -> str:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key or "..." in key:
        raise RuntimeError("Thiếu OPENAI_API_KEY hợp lệ trong .env (hoặc biến môi trường).")
    return key


def _unique_sources(chunks: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        source = metadata.get("source")
        if not source:
            continue
        source = str(source)
        if source in seen:
            continue
        seen.add(source)
        ordered.append(source)
    return ordered


def _intersection_size(a: list[str], b: list[str]) -> int:
    set_b = set(b)
    return sum(1 for item in a if item in set_b)


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    should_answer: bool
    expected_sources: list[str]
    got_sources: list[str]
    answered: bool
    refused: bool
    citations_valid: bool
    context_recall: float
    context_precision: float
    answer_relevancy: float
    faithfulness: float


def score_case(
    *,
    case_id: str,
    should_answer: bool,
    expected_sources: list[str],
    answer: str,
    sources: list[dict[str, Any]],
    citations_valid: bool,
) -> CaseScore:
    got_sources = _unique_sources(sources)
    hits = _intersection_size(got_sources, expected_sources)

    refused = (answer or "").strip() == REFUSAL_MESSAGE
    answered = bool((answer or "").strip()) and not refused

    # Context metrics: dựa trên source filenames trong golden_dataset.json.
    if not should_answer:
        # Out-of-domain: lý tưởng là từ chối và không đưa evidence.
        context_recall = 1.0 if not got_sources else 0.0
        context_precision = 1.0 if not got_sources else 0.0
    else:
        denom_recall = max(1, len(expected_sources))
        context_recall = hits / denom_recall
        context_precision = hits / max(1, len(got_sources)) if got_sources else 0.0

    # Proxy metrics (không phải RAGAS):
    # - Answer relevancy: đúng hành vi (trả lời khi nên, từ chối khi không nên).
    # - Faithfulness: yêu cầu citation hợp lệ khi có trả lời.
    if should_answer:
        answer_relevancy = 1.0 if answered else 0.0
        faithfulness = 1.0 if (answered and citations_valid) else (0.0 if answered else 0.0)
    else:
        answer_relevancy = 1.0 if refused else 0.0
        faithfulness = 1.0 if refused else 0.0

    return CaseScore(
        case_id=case_id,
        should_answer=should_answer,
        expected_sources=list(expected_sources),
        got_sources=got_sources,
        answered=answered,
        refused=refused,
        citations_valid=bool(citations_valid),
        context_recall=round(float(context_recall), 4),
        context_precision=round(float(context_precision), 4),
        answer_relevancy=round(float(answer_relevancy), 4),
        faithfulness=round(float(faithfulness), 4),
    )


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values)) / float(len(values))


def _extract_contexts(
    sources: list[dict[str, Any]],
    *,
    max_chars_per_chunk: int | None,
) -> list[str]:
    contexts: list[str] = []
    for item in sources:
        content = str(item.get("content") or "").strip()
        metadata = item.get("metadata") or {}
        source = str(metadata.get("source") or "")
        if source:
            content = f"SOURCE: {source}\n{content}"
        if max_chars_per_chunk is not None and max_chars_per_chunk > 0:
            content = content[:max_chars_per_chunk]
        if content:
            contexts.append(content)
    return contexts


def evaluate_config(
    *,
    config_name: str,
    runner,
    dataset: list[dict[str, Any]],
    limit: int | None,
    max_chars_per_chunk: int | None,
) -> tuple[dict[str, float], list[CaseScore], list[dict[str, Any]]]:
    scores: list[CaseScore] = []
    raw_rows: list[dict[str, Any]] = []

    items = dataset[:limit] if limit else dataset
    for index, item in enumerate(items, start=1):
        case_id = str(item.get("id", f"case_{index}"))
        question = str(item["question"])
        should_answer = bool(item.get("should_answer", True))
        expected_sources = [str(s) for s in (item.get("expected_sources") or [])]
        expected_answer = str(item.get("expected_answer") or "")

        try:
            result = runner(question)
        except Exception as exc:
            result = {
                "answer": "",
                "sources": [],
                "citations_valid": False,
                "error": repr(exc),
            }

        answer = str(result.get("answer") or "")
        sources = result.get("sources") or []
        if not isinstance(sources, list):
            sources = []
        contexts = _extract_contexts(sources, max_chars_per_chunk=max_chars_per_chunk)

        case_score = score_case(
            case_id=case_id,
            should_answer=should_answer,
            expected_sources=expected_sources,
            answer=answer,
            sources=sources,
            citations_valid=bool(result.get("citations_valid", False)),
        )
        scores.append(case_score)
        raw_rows.append(
            {
                "config": config_name,
                "id": case_id,
                "question": question,
                "should_answer": should_answer,
                "expected_sources": expected_sources,
                "ground_truth": expected_answer,
                "answer": answer,
                "contexts": contexts,
                "got_sources": case_score.got_sources,
                "citations_valid": case_score.citations_valid,
                "error": result.get("error"),
                "metrics": {
                    "faithfulness_proxy": case_score.faithfulness,
                    "answer_relevancy_proxy": case_score.answer_relevancy,
                    "context_recall_proxy": case_score.context_recall,
                    "context_precision_proxy": case_score.context_precision,
                },
            }
        )

    summary = {
        "faithfulness_proxy": round(mean([s.faithfulness for s in scores]), 4),
        "answer_relevancy_proxy": round(mean([s.answer_relevancy for s in scores]), 4),
        "context_recall_proxy": round(mean([s.context_recall for s in scores]), 4),
        "context_precision_proxy": round(mean([s.context_precision for s in scores]), 4),
        "average_proxy": round(
            mean(
                [
                    mean([s.faithfulness for s in scores]),
                    mean([s.answer_relevancy for s in scores]),
                    mean([s.context_recall for s in scores]),
                    mean([s.context_precision for s in scores]),
                ]
            ),
            4,
        ),
    }
    return summary, scores, raw_rows


def build_runner(*, retrieval_mode: str, use_reranking: bool, use_pageindex_fallback: bool):
    from src.task10_generation import generate_with_citation

    def run(question: str) -> dict[str, Any]:
        return generate_with_citation(
            question,
            retrieval_mode=retrieval_mode,
            use_reranking=use_reranking,
            use_pageindex_fallback=use_pageindex_fallback,
        )

    return run


def evaluate_with_ragas(
    rows: list[dict[str, Any]],
    *,
    judge_model: str,
    embedding_model: str,
    strict: bool,
) -> tuple[dict[str, float], dict[str, int]]:
    """
    Chạy RAGAS metrics thật cho một config.

    Dataset schema (RAGAS 0.1.x) dùng:
      - question: str
      - answer: str
      - contexts: list[str]
      - ground_truth: str
    """

    require_openai_key()

    from datasets import Dataset, Features, Sequence, Value
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    payload = [
        {
            "question": str(row.get("question") or ""),
            "answer": str(row.get("answer") or ""),
            "contexts": list(row.get("contexts") or []),
            "ground_truth": str(row.get("ground_truth") or ""),
        }
        for row in rows
    ]
    features = Features(
        {
            "question": Value("string"),
            "answer": Value("string"),
            "contexts": Sequence(Value("string")),
            "ground_truth": Value("string"),
        }
    )
    ds = Dataset.from_list(payload, features=features)

    llm = ChatOpenAI(model=judge_model, temperature=0)
    embeddings = OpenAIEmbeddings(model=embedding_model)

    metrics = [faithfulness, answer_relevancy, context_recall, context_precision]
    result = evaluate(
        ds,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=strict,
    )

    nan_counts: dict[str, int] = {}
    for metric in ("faithfulness", "answer_relevancy", "context_recall", "context_precision"):
        values = list(result.scores[metric])
        nan_counts[metric] = sum(
            1
            for v in values
            if v is None or (isinstance(v, float) and math.isnan(v))
        )

    summary = {
        "faithfulness": round(float(result["faithfulness"]), 4),
        "answer_relevancy": round(float(result["answer_relevancy"]), 4),
        "context_recall": round(float(result["context_recall"]), 4),
        "context_precision": round(float(result["context_precision"]), 4),
    }
    summary["average"] = round(
        mean(
            [
                summary["faithfulness"],
                summary["answer_relevancy"],
                summary["context_recall"],
                summary["context_precision"],
            ]
        ),
        4,
    )
    return summary, nan_counts


def export_markdown(
    *,
    output_path: Path,
    generated_at: str,
    command: str,
    dataset_size: int,
    proxy_summaries: dict[str, dict[str, float]] | None,
    ragas_summaries: dict[str, dict[str, float]] | None,
    ragas_nan_counts: dict[str, dict[str, int]] | None,
    judge_model: str | None,
    embedding_model: str | None,
) -> None:
    def _fmt(value: float) -> str:
        return "N/A" if isinstance(value, float) and math.isnan(value) else str(value)

    def _fmt_delta(a: float, b: float) -> str:
        if (isinstance(a, float) and math.isnan(a)) or (isinstance(b, float) and math.isnan(b)):
            return "N/A"
        return f"{(float(a) - float(b)):+.4f}"

    def _table_row(summaries: dict[str, dict[str, float]], metric_key: str, label: str) -> str:
        a = summaries["Config A (Hybrid)"][metric_key]
        b = summaries["Config B (Dense-only)"][metric_key]
        return f"| **{label}** | {_fmt(a)} | {_fmt(b)} | {_fmt_delta(a, b)} |"

    def _nan_note(metric_key: str) -> str:
        if not ragas_nan_counts:
            return ""
        a_nan = ragas_nan_counts["Config A (Hybrid)"].get(metric_key, 0)
        b_nan = ragas_nan_counts["Config B (Dense-only)"].get(metric_key, 0)
        if a_nan == 0 and b_nan == 0:
            return ""
        return f" _(NaN rows: A={a_nan}, B={b_nan})_"

    header = f"""# RAG Evaluation Results — Group C3-02

> Generated at: **{generated_at}**
>
> Command: `{command}`
>
> Dataset: `{GOLDEN_DATASET_PATH.as_posix()}` ({dataset_size} cases)
"""

    sections: list[str] = [header]

    if ragas_summaries:
        judge = judge_model or DEFAULT_JUDGE_MODEL
        embed = embedding_model or DEFAULT_EMBED_MODEL
        sections.append(
            f"""
## Overall (RAGAS Metrics)

> Judge model: `{judge}`
>
> Embeddings: `{embed}`

| Metric | Config A (Hybrid) | Config B (Dense-only) | Δ (A - B) |
|---|---:|---:|---:|
{_table_row(ragas_summaries, "faithfulness", "Faithfulness")}{_nan_note("faithfulness")}
{_table_row(ragas_summaries, "answer_relevancy", "Answer Relevancy")}{_nan_note("answer_relevancy")}
{_table_row(ragas_summaries, "context_recall", "Context Recall")}{_nan_note("context_recall")}
{_table_row(ragas_summaries, "context_precision", "Context Precision")}{_nan_note("context_precision")}
{_table_row(ragas_summaries, "average", "Average")}
"""
        )

    if proxy_summaries:
        sections.append(
            f"""
## Overall (Proxy Metrics)

> Proxy metrics dùng để chạy offline/nhanh, **không phải** RAGAS chính thức.

| Metric | Config A (Hybrid) | Config B (Dense-only) | Δ (A - B) |
|---|---:|---:|---:|
{_table_row(proxy_summaries, "faithfulness_proxy", "Faithfulness (proxy)")}
{_table_row(proxy_summaries, "answer_relevancy_proxy", "Answer relevancy (proxy)")}
{_table_row(proxy_summaries, "context_recall_proxy", "Context recall (proxy)")}
{_table_row(proxy_summaries, "context_precision_proxy", "Context precision (proxy)")}
{_table_row(proxy_summaries, "average_proxy", "Average (proxy)")}
"""
        )

    output_path.write_text("\n".join(sections).strip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Giới hạn số câu để chạy (0 = all).")
    parser.add_argument(
        "--mode",
        choices=["ragas", "proxy", "both"],
        default="ragas",
        help="Chọn kiểu đánh giá: ragas (thật), proxy (offline), hoặc both.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Nếu bật, lỗi trong RAGAS sẽ raise (thay vì trả NaN).",
    )
    parser.add_argument(
        "--judge-model",
        default=DEFAULT_JUDGE_MODEL,
        help="Model OpenAI dùng làm LLM-judge cho RAGAS.",
    )
    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBED_MODEL,
        help="Model OpenAI dùng làm embeddings cho RAGAS (AnswerRelevancy).",
    )
    parser.add_argument(
        "--context-max-chars",
        type=int,
        default=1800,
        help="Giới hạn ký tự mỗi chunk context khi feed vào RAGAS/LLM (0 = không giới hạn).",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Đường dẫn file Markdown output (mặc định: results.generated.md).",
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="Lưu raw outputs để audit tại group_project/evaluation/eval_outputs.json",
    )
    args = parser.parse_args()

    dataset = load_golden_dataset()
    if args.mode in ("ragas", "both"):
        require_openai_key()

    runner_a = build_runner(retrieval_mode="hybrid", use_reranking=True, use_pageindex_fallback=True)
    runner_b = build_runner(retrieval_mode="dense_only", use_reranking=False, use_pageindex_fallback=False)

    limit = int(args.limit) if int(args.limit) > 0 else None
    max_chars_per_chunk = None if int(args.context_max_chars) <= 0 else int(args.context_max_chars)

    proxy_summary_a, _, raw_a = evaluate_config(
        config_name="Config A (Hybrid)",
        runner=runner_a,
        dataset=dataset,
        limit=limit,
        max_chars_per_chunk=max_chars_per_chunk,
    )
    proxy_summary_b, _, raw_b = evaluate_config(
        config_name="Config B (Dense-only)",
        runner=runner_b,
        dataset=dataset,
        limit=limit,
        max_chars_per_chunk=max_chars_per_chunk,
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    command = " ".join([Path(sys.argv[0]).as_posix(), *sys.argv[1:]]).strip()

    proxy_summaries = {
        "Config A (Hybrid)": proxy_summary_a,
        "Config B (Dense-only)": proxy_summary_b,
    } if args.mode in ("proxy", "both") else None

    ragas_summaries = None
    ragas_nan_counts = None
    if args.mode in ("ragas", "both"):
        ragas_a, nan_a = evaluate_with_ragas(
            raw_a,
            judge_model=str(args.judge_model),
            embedding_model=str(args.embedding_model),
            strict=bool(args.strict),
        )
        ragas_b, nan_b = evaluate_with_ragas(
            raw_b,
            judge_model=str(args.judge_model),
            embedding_model=str(args.embedding_model),
            strict=bool(args.strict),
        )
        ragas_summaries = {
            "Config A (Hybrid)": ragas_a,
            "Config B (Dense-only)": ragas_b,
        }
        ragas_nan_counts = {
            "Config A (Hybrid)": nan_a,
            "Config B (Dense-only)": nan_b,
        }

    export_markdown(
        output_path=Path(args.output),
        generated_at=generated_at,
        command=command or "python group_project/evaluation/eval_pipeline.py",
        dataset_size=len(dataset[:limit] if limit else dataset),
        proxy_summaries=proxy_summaries,
        ragas_summaries=ragas_summaries,
        ragas_nan_counts=ragas_nan_counts,
        judge_model=str(args.judge_model) if args.mode in ("ragas", "both") else None,
        embedding_model=str(args.embedding_model) if args.mode in ("ragas", "both") else None,
    )

    if args.save_json:
        output_path = EVAL_DIR / "eval_outputs.json"
        output_path.write_text(
            json.dumps(
                {
                    "generated_at": generated_at,
                    "dataset_size": len(dataset[:limit] if limit else dataset),
                    "configs": ["Config A (Hybrid)", "Config B (Dense-only)"],
                    "rows": [*raw_a, *raw_b],
                    "mode": args.mode,
                    "judge_model": str(args.judge_model),
                    "embedding_model": str(args.embedding_model),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    print(f"✅ Wrote report: {Path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
