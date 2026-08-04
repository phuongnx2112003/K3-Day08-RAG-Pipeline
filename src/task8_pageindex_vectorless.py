"""Task 8 — PageIndex vectorless fallback.

PageIndex Cloud chỉ nhận PDF. Module ghép corpus Markdown thành một PDF có cấu trúc,
upload một lần và lưu ``doc_id`` cục bộ. Các lần fallback sau chỉ gửi query tới
document đó và trả cùng contract với hybrid retrieval.
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STANDARDIZED_DIR = PROJECT_ROOT / "data" / "standardized"
PAGEINDEX_PDF_DIR = PROJECT_ROOT / "pageindex_pdfs"
COMBINED_PDF_PATH = PAGEINDEX_PDF_DIR / "book_review_corpus.pdf"
REGISTRY_PATH = PROJECT_ROOT / "pageindex_doc_ids.json"
PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "").strip()

DEFAULT_POLL_INTERVAL = 3.0
DEFAULT_TIMEOUT = 300.0
RECOMMENDED_FALLBACK_THRESHOLD = 0.4
READY_STATUSES = {"completed", "complete", "ready", "success", "succeeded"}
FAILED_STATUSES = {"failed", "error", "cancelled", "canceled"}
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _require_api_key() -> str:
    if not PAGEINDEX_API_KEY or "..." in PAGEINDEX_API_KEY:
        raise RuntimeError("PAGEINDEX_API_KEY chưa được cấu hình hợp lệ trong .env")
    return PAGEINDEX_API_KEY


def _client():
    from pageindex import PageIndexClient

    return PageIndexClient(api_key=_require_api_key())


def _find_unicode_font() -> Path:
    candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Không tìm thấy font Unicode để tạo PDF cho PageIndex")


def _pdf_safe_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = text.replace("‐", "-").replace("❖", "*")
    return _CONTROL_RE.sub(" ", text)


def build_combined_pdf(output_path: Path = COMBINED_PDF_PATH) -> Path:
    """Ghép toàn bộ Markdown thành một PDF, giữ heading/source cho citation."""

    try:
        from fpdf import FPDF
    except ImportError as exc:  # pragma: no cover - dependency trong requirements.txt
        raise RuntimeError("Cần cài fpdf2 để tạo PDF PageIndex") from exc

    markdown_files = sorted(STANDARDIZED_DIR.rglob("*.md"))
    if not markdown_files:
        raise RuntimeError(f"Không có Markdown trong {STANDARDIZED_DIR}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("CorpusUnicode", fname=str(_find_unicode_font()))

    for document_index, path in enumerate(markdown_files, start=1):
        pdf.add_page()
        pdf.set_font("CorpusUnicode", size=15)
        pdf.multi_cell(
            0,
            8,
            _pdf_safe_text(f"DOCUMENT {document_index}: {path.name}"),
            new_x="LMARGIN",
            new_y="NEXT",
            wrapmode="CHAR",
        )
        pdf.set_font("CorpusUnicode", size=9)
        relative = path.relative_to(STANDARDIZED_DIR).as_posix()
        pdf.multi_cell(
            0,
            5,
            f"SOURCE_FILE: {relative}",
            new_x="LMARGIN",
            new_y="NEXT",
            wrapmode="CHAR",
        )
        pdf.ln(2)
        pdf.set_font("CorpusUnicode", size=10)
        content = _pdf_safe_text(path.read_text(encoding="utf-8", errors="strict"))
        pdf.multi_cell(
            0,
            5,
            content,
            new_x="LMARGIN",
            new_y="NEXT",
            wrapmode="CHAR",
        )

    pdf.output(str(output_path))
    return output_path


def _read_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"documents": []}
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"documents": []}
    return payload if isinstance(payload, dict) else {"documents": []}


def _write_registry(documents: list[dict[str, Any]]) -> None:
    payload = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "documents": documents,
    }
    REGISTRY_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _document_id(response: dict[str, Any]) -> str:
    doc_id = response.get("doc_id") or response.get("id")
    if not doc_id and isinstance(response.get("document"), dict):
        doc_id = response["document"].get("id") or response["document"].get("doc_id")
    if not doc_id:
        raise RuntimeError(f"PageIndex response không có doc_id: {response}")
    return str(doc_id)


def get_registered_doc_ids() -> list[str]:
    documents = _read_registry().get("documents", [])
    return [
        str(item["doc_id"])
        for item in documents
        if isinstance(item, dict) and item.get("doc_id")
    ]


def wait_until_document_ready(
    doc_id: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
) -> bool:
    """Poll tree status cho tới khi document sẵn sàng hoặc timeout."""

    client = _client()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if client.is_retrieval_ready(doc_id):
            return True
        time.sleep(max(0.1, poll_interval))
    return False


def upload_documents(
    *,
    force: bool = False,
    wait: bool = True,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    """Tạo một PDF tổng hợp và upload lên PageIndex Cloud.

    Nếu registry đã có doc_id thì không upload lại, trừ khi ``force=True``.
    """

    existing = _read_registry().get("documents", [])
    if existing and not force:
        return [dict(item) for item in existing if isinstance(item, dict)]

    pdf_path = build_combined_pdf()
    response = _client().submit_document(str(pdf_path))
    doc_id = _document_id(response)
    record: dict[str, Any] = {
        "doc_id": doc_id,
        "name": pdf_path.name,
        "source_count": len(list(STANDARDIZED_DIR.rglob("*.md"))),
        "status": "submitted",
    }
    _write_registry([record])

    if wait:
        ready = wait_until_document_ready(doc_id, timeout=timeout)
        record["status"] = "ready" if ready else "processing"
        _write_registry([record])
    return [record]


def _retrieval_id(response: dict[str, Any]) -> str | None:
    value = response.get("retrieval_id") or response.get("id")
    if not value and isinstance(response.get("retrieval"), dict):
        value = response["retrieval"].get("id")
    return str(value) if value else None


def _retrieval_status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or payload.get("state") or "").strip().lower()


def _wait_for_retrieval(
    client: Any,
    retrieval_id: str,
    *,
    timeout: float,
    poll_interval: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_payload: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last_payload = client.get_retrieval(retrieval_id)
        status = _retrieval_status(last_payload)
        if status in READY_STATUSES or last_payload.get("retrieved_nodes"):
            return last_payload
        if status in FAILED_STATUSES:
            raise RuntimeError(f"PageIndex retrieval thất bại: {last_payload}")
        time.sleep(max(0.1, poll_interval))
    raise TimeoutError(f"PageIndex retrieval timeout: {retrieval_id}")


def _walk_relevant_contents(value: Any, context: dict[str, Any] | None = None):
    """Duyệt schema retrieval cũ/mới mà không phụ thuộc độ lồng list."""

    context = dict(context or {})
    if isinstance(value, dict):
        for source_key, target_key in (
            ("section_title", "section"),
            ("title", "section"),
            ("node_id", "node_id"),
            ("page", "page"),
            ("page_num", "page"),
        ):
            if value.get(source_key) is not None:
                context[target_key] = value[source_key]

        content = (
            value.get("relevant_content")
            or value.get("content")
            or value.get("text")
        )
        if isinstance(content, str) and content.strip():
            yield content.strip(), context

        for key, child in value.items():
            if key not in {"relevant_content", "content", "text"}:
                yield from _walk_relevant_contents(child, context)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_relevant_contents(child, context)


def parse_retrieval_results(
    payload: dict[str, Any],
    *,
    doc_id: str,
    top_k: int,
) -> list[dict]:
    """Chuyển PageIndex response về contract retrieval chung."""

    root = payload.get("retrieved_nodes", payload)
    results: list[dict] = []
    seen: set[str] = set()
    for content, context in _walk_relevant_contents(root):
        if content in seen:
            continue
        seen.add(content)
        rank = len(results) + 1
        results.append(
            {
                "content": content,
                "score": round(1.0 / rank, 4),
                "metadata": {
                    **context,
                    "doc_id": doc_id,
                    "retrieval_id": payload.get("retrieval_id") or payload.get("id", ""),
                    "retrieval_method": "pageindex",
                },
                "source": "pageindex",
            }
        )
        if len(results) >= top_k:
            break
    return results


def pageindex_search(
    query: str,
    top_k: int = 5,
    *,
    doc_ids: Sequence[str] | None = None,
    thinking: bool = False,
    timeout: float = 120.0,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    strict: bool = False,
) -> list[dict]:
    """Vectorless retrieval dùng làm fallback khi dense cosine quá thấp."""

    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not isinstance(top_k, int):
        raise TypeError("top_k must be an integer")
    if top_k <= 0 or not query.strip():
        return []

    selected_doc_ids = [str(value) for value in (doc_ids or get_registered_doc_ids()) if value]
    if not selected_doc_ids:
        if strict:
            raise RuntimeError("Chưa có PageIndex doc_id. Hãy chạy upload_documents()")
        return []

    try:
        client = _client()
        combined: list[dict] = []
        for doc_id in selected_doc_ids:
            submitted = client.submit_query(doc_id=doc_id, query=query, thinking=thinking)
            retrieval_id = _retrieval_id(submitted)
            if retrieval_id:
                payload = _wait_for_retrieval(
                    client,
                    retrieval_id,
                    timeout=timeout,
                    poll_interval=poll_interval,
                )
                payload.setdefault("retrieval_id", retrieval_id)
            else:
                payload = submitted
            combined.extend(parse_retrieval_results(payload, doc_id=doc_id, top_k=top_k))

        combined.sort(key=lambda item: item["score"], reverse=True)
        return combined[:top_k]
    except Exception as exc:
        if strict:
            raise
        print(f"PageIndex fallback unavailable: {exc}")
        return []


def should_fallback(
    dense_results: Sequence[dict],
    score_threshold: float = RECOMMENDED_FALLBACK_THRESHOLD,
) -> bool:
    """Quyết định fallback bằng cosine gốc của dense search, không dùng RRF score."""

    if not 0.0 <= score_threshold <= 1.0:
        raise ValueError("score_threshold must be between 0 and 1")
    if not dense_results:
        return True
    best_dense_score = max(float(item.get("score", 0.0)) for item in dense_results)
    return best_dense_score < score_threshold


if __name__ == "__main__":
    ids = get_registered_doc_ids()
    if not ids:
        print("Chưa có PageIndex document. Chạy upload_documents() trước.")
    else:
        results = pageindex_search(
            "Summarize the core knowledge in this corpus",
            top_k=3,
            strict=True,
        )
        for result in results:
            print(f"[{result['score']:.4f}] {result['content'][:100]}...")
