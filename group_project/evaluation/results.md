# RAG Evaluation Results

Framework: **offline lexical proxy (install ragas + datasets for LLM judging)**

> Offline proxy metrics are lexical diagnostics only. Run `python3 group_project/evaluation/eval_pipeline.py` after installing RAGAS and configuring OpenAI to obtain the required LLM-judged metrics.

## Overall Scores

| Metric | Score |
|---|---:|
| Faithfulness | 0.7259 |
| Answer Relevance | 0.0677 |
| Context Recall | 0.0965 |
| Context Precision | 0.0121 |

## A/B Comparison

| Metric | A: hybrid + Jina rerank | B: hybrid no rerank | Δ |
|---|---:|---:|---:|
| Faithfulness | 0.9500 | 0.9500 | +0.0000 |
| Answer Relevance | 0.0965 | 0.0965 | +0.0000 |
| Context Recall | 0.0965 | 0.0965 | +0.0000 |
| Context Precision | 0.0121 | 0.0121 | +0.0000 |

## Worst Performers (offline diagnostic)

| Question | Faithfulness | Answer relevance | Context recall | Context precision |
|---|---:|---:|---:|---:|
| Bốn bước hình thành thói quen là gì? | 0.000 | 0.000 | 0.000 | 0.000 |
| Học phí chương trình Business tại RMIT Vietnam là bao nhiêu? | 0.712 | 0.000 | 0.000 | 0.007 |
| The Innovators nói về chủ đề gì? | 0.742 | 0.000 | 0.000 | 0.003 |

## Recommendations

1. Run the RAGAS path with a configured OpenAI judge before presentation; record the generated report.
2. Inspect low-recall questions and add concise, rights-cleared source passages where corpus evidence is absent.
3. Calibrate the dense threshold using in-domain and out-of-domain queries; PageIndex should remain an optional remote fallback.
