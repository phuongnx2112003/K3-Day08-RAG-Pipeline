# RAG Evaluation Results — Group C3-02

> Generated at: **2026-08-04T15:28:19.540252+00:00**
>
> Command: `group_project/evaluation/eval_pipeline.py --mode ragas --save-json --output group_project/evaluation/results.md`
>
> Dataset: `D:/K3-Day08-RAG-Pipeline/group_project/evaluation/golden_dataset.json` (19 cases)


## Overall (RAGAS Metrics)

> Judge model: `gpt-4.1-mini`
>
> Embeddings: `text-embedding-3-small`

| Metric | Config A (Hybrid) | Config B (Dense-only) | Δ (A - B) |
|---|---:|---:|---:|
| **Faithfulness** | 0.8835 | 0.8194 | +0.0641 |
| **Answer Relevancy** | 0.5961 | 0.5878 | +0.0083 |
| **Context Recall** | 0.8947 | 0.8947 | +0.0000 |
| **Context Precision** | 0.8025 | 0.7979 | +0.0046 |
| **Average** | 0.7942 | 0.775 | +0.0192 |
