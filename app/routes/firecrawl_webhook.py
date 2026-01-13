import hashlib
import json
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import FirecrawlEvent, Document
from ..security import verify_firecrawl_signature
from ..schemas import FirecrawlWebhookEvent
from ..rag_pipeline import ingest_markdown_to_qdrant

router = APIRouter(prefix="/v1/hooks", tags=["webhooks"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def doc_key(business_slug: str, source_id: str, url: str) -> str:
    return hashlib.sha256(f"{business_slug}|{source_id}|{url}".encode("utf-8")).hexdigest()


@router.post("/firecrawl-ingest")
async def firecrawl_ingest(
    request: Request,
    raw_body: bytes = Depends(verify_firecrawl_signature),
    db: Session = Depends(get_db),
):
    # Parse JSON from raw body
    try:
        payload_dict = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = FirecrawlWebhookEvent.model_validate(payload_dict)

    # 1) Idempotency at EVENT level
    body_hash = sha256_hex(raw_body)

    event_row = FirecrawlEvent(
        event_id=event.id,
        event_type=event.type,
        signature=request.headers.get("X-Firecrawl-Signature"),
        raw_body_sha256=body_hash,
        payload=payload_dict,
    )

    try:
        db.add(event_row)
        db.commit()
    except IntegrityError:
        db.rollback()
        # duplicate event -> ignore safely
        return {"ok": True, "deduped": True, "event_id": event.id, "type": event.type}

    # 2) Only ingest documents on per-page event types
    # Firecrawl supports crawl.page, crawl.completed, crawl.failed, etc. :contentReference[oaicite:4]{index=4}
    if event.type not in ("crawl.page", "batch.page", "scrape.completed"):
        # store event already; nothing else needed
        return {"ok": True, "event_id": event.id, "type": event.type}

    # 3) Enforce tenant/source mapping
    business_slug = str(event.metadata.get("business_slug") or "")
    source_id = str(event.metadata.get("source_id") or "")
    crawl_job_id = str(event.metadata.get("crawl_job_id") or event.id or "")

    if not business_slug or not source_id:
        raise HTTPException(
            status_code=400,
            detail="Missing required metadata: business_slug and source_id",
        )

    # Firecrawl "data" can include one or more docs per event
    processed = 0
    skipped_unchanged = 0

    for item in event.data:
        # Flexible extraction: Firecrawl doc shape varies by event.
        # Common fields: markdown/html/metadata.source_url or source_url/url.
        md = item.get("markdown") or item.get("content")
        url = (
            (item.get("metadata") or {}).get("source_url")
            or item.get("source_url")
            or item.get("url")
        )

        if not url or not md:
            # ignore malformed doc
            continue

        md_str = str(md)
        url_str = str(url)

        # 4) Document idempotency (overwrite latest, but skip if unchanged)
        key = doc_key(business_slug, source_id, url_str)
        content_hash = hashlib.sha256(md_str.encode("utf-8")).hexdigest()

        existing = db.query(Document).filter(Document.doc_key == key).one_or_none()
        if existing and existing.content_hash == content_hash:
            skipped_unchanged += 1
            continue

        doc_json = {
            "business_slug": business_slug,
            "source_id": source_id,
            "crawl_job_id": crawl_job_id,
            "url": url_str,
            "content": {"markdown": md_str},
            "metadata": {
                # Keep original metadata for debugging and future ranking
                "firecrawl": item.get("metadata") or {},
                "received_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            },
        }

        if existing:
            existing.content_hash = content_hash
            existing.content = doc_json
            existing.crawl_job_id = crawl_job_id
            existing.updated_at = dt.datetime.now(dt.timezone.utc)
        else:
            db.add(
                Document(
                    doc_key=key,
                    business_slug=business_slug,
                    source_id=source_id,
                    url=url_str,
                    content_hash=content_hash,
                    content=doc_json,
                    crawl_job_id=crawl_job_id,
                )
            )

        db.commit()

        # 5) Trigger RAG ingestion per document (real-time)
        ingest_markdown_to_qdrant(
            business_slug=business_slug,
            source_id=source_id,
            url=url_str,
            markdown=md_str,
            doc_metadata=doc_json.get("metadata"),
            crawl_job_id=crawl_job_id,
        )

        processed += 1

    return {
        "ok": True,
        "event_id": event.id,
        "type": event.type,
        "processed": processed,
        "skipped_unchanged": skipped_unchanged,
    }
