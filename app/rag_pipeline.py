import hashlib
from typing import Any, Dict, Optional

# This module is the integration point your teammate can own later.
# For now, it’s a stub that you can connect to his real implementation.

def stable_vector_id(company_id: str, source_id: str, url: str) -> str:
    """
    Stable ID for overwrite-latest upserts:
    Use URL (or hash of it) – teammate wants URL/hash as ID.
    We include company/source too, to avoid collisions in one collection.
    """
    raw = f"{company_id}|{source_id}|{url}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def ingest_markdown_to_qdrant(
    *,
    company_id: str,
    source_id: str,
    url: str,
    markdown: str,
    doc_metadata: Optional[Dict[str, Any]] = None,
    crawl_job_id: Optional[str] = None,
) -> None:
    """
    Call the teammate's RAG pipeline here.
    Should:
    - chunk markdown (preserving headers/lists)
    - compute embeddings
    - upsert into Qdrant collection with metadata:
        company_id, source_id, url, crawl_job_id, ...
    """
    vector_doc_id = stable_vector_id(company_id, source_id, url)

    # TODO: Replace with teammate function call, e.g.
    # from app.tools.rag import upsert_markdown_document
    # upsert_markdown_document(
    #   collection="finnish_tax_law",
    #   point_id=vector_doc_id,
    #   markdown=markdown,
    #   payload={"company_id": company_id, "source_id": source_id, "url": url, **(doc_metadata or {})},
    # )

    # For now, just log:
    print(f"[RAG] Upsert {vector_doc_id} url={url} company_id={company_id} source_id={source_id} len={len(markdown)}")
