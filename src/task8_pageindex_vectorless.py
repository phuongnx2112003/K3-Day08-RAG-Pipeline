"""Task 8 — Optional PageIndex vectorless fallback.

The PageIndex account owns document IDs, so they are deliberately kept out of
source control in ``pageindex_doc_ids.json`` (already ignored by git).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
DOCUMENT_IDS_PATH = PROJECT_ROOT / "pageindex_doc_ids.json"
PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")


def _client():
    if not PAGEINDEX_API_KEY:
        return None
    try:
        from pageindex.client import PageIndexClient
        return PageIndexClient(api_key=PAGEINDEX_API_KEY)
    except ImportError:
        return None


def _load_document_ids() -> list[str]:
    if not DOCUMENT_IDS_PATH.exists():
        return []
    data = json.loads(DOCUMENT_IDS_PATH.read_text(encoding="utf-8"))
    return list(data.values()) if isinstance(data, dict) else list(data)


def upload_documents(files: list[str] | None = None) -> dict[str, str]:
    """Upload PDF documents and persist their PageIndex document IDs locally."""
    client = _client()
    if client is None:
        return {}
    pdfs = [Path(path) for path in files] if files else list((PROJECT_ROOT / "data/landing/legal").glob("*.pdf"))
    document_ids = dict(zip((path.name for path in pdfs), _load_document_ids()))
    for path in pdfs:
        if path.name in document_ids:
            continue
        response = client.submit_document(str(path))
        doc_id = response.get("doc_id") or response.get("id")
        if doc_id:
            document_ids[path.name] = doc_id
    DOCUMENT_IDS_PATH.write_text(json.dumps(document_ids, ensure_ascii=False, indent=2), encoding="utf-8")
    return document_ids


def _parse_nodes(payload: dict, top_k: int) -> list[dict]:
    results: list[dict] = []
    for node in payload.get("retrieved_nodes", []):
        for group in node.get("relevant_contents", []):
            for item in group:
                content = item.get("relevant_content", "")
                if content:
                    results.append({"content": content, "score": 1.0 / (len(results) + 1),
                                    "metadata": {"section": item.get("section_title", "")}, "source": "pageindex"})
                    if len(results) >= top_k:
                        return results
    return results


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Query registered PageIndex documents; return ``[]`` when not configured."""
    if not query or not query.strip() or top_k <= 0:
        return []
    client, document_ids = _client(), _load_document_ids()
    if client is None or not document_ids:
        return []
    results: list[dict] = []
    for doc_id in document_ids:
        try:
            submitted = client.submit_query(doc_id=doc_id, query=query)
            retrieval_id = submitted.get("retrieval_id") or submitted.get("id")
            if not retrieval_id:
                continue
            retrieval = client.get_retrieval(retrieval_id)
            for _ in range(12):
                if retrieval.get("status") in {"completed", "complete"}:
                    break
                time.sleep(1)
                retrieval = client.get_retrieval(retrieval_id)
            results.extend(_parse_nodes(retrieval, top_k - len(results)))
            if len(results) >= top_k:
                break
        except Exception:
            # PageIndex is an optional remote fallback; hybrid retrieval remains usable.
            continue
    return results[:top_k]
