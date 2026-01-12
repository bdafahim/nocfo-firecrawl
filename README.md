# NoCFO Firecrawl Ingestion Backend

A secure, tenant-aware webhook ingestion backend for NoCFO that receives Firecrawl events, persists normalized documents, and triggers real-time RAG ingestion for downstream AI agents.

## Overview

This service provides per-page webhook ingestion with strong guarantees around tenant isolation, idempotency, and data freshness. It's designed to be safe, scalable, and production-ready.

### Key Features

- **Per-page webhook ingestion** - Streaming, not batch processing
- **Real-time RAG triggers** - Documents processed immediately per page
- **Overwrite-latest semantics** - Vectors upserted by URL hash
- **JSON storage with Markdown** - Markdown is canonical for embeddings
- **Tenant isolation** - Via `company_id` + `source_id`
- **Webhook signature verification** - HMAC-SHA256 security
- **Full idempotency** - Event and document-level deduplication


## Getting Started

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)

### Installation

1. **Create virtual environment**
   ```bash
   cd firecrawl-backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set your local values (do not commit this file).

4. **Start the server**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. **Health check**
   ```bash
   curl http://127.0.0.1:8000/health
   ```
   
   Expected response:
   ```json
   { "ok": true }
   ```

## Local Testing

This test simulates Firecrawl calling your webhook and validates signature verification, idempotency, DB writes, and RAG triggers.

### Step 1: Create Test Payload

Create `test_firecrawl_payload.json` in the project root:

```json
{
  "success": true,
  "type": "crawl.page",
  "id": "evt_test_001",
  "metadata": {
    "company_id": "company_123",
    "source_id": "vero",
    "crawl_job_id": "crawl_test_001"
  },
  "data": [
    {
      "markdown": "# Tax Deduction\n\nThis page explains tax deductions in Finland.",
      "metadata": {
        "source_url": "https://vero.fi/tax-deduction"
      }
    }
  ]
}
```

### Step 2: Generate Webhook Signature

```bash
python - <<'EOF'
import hmac, hashlib, pathlib

secret = b"your-firecrawl-webhook-secret"
body = pathlib.Path("test_firecrawl_payload.json").read_bytes()

sig = hmac.new(secret, body, hashlib.sha256).hexdigest()
print("sha256=" + sig)
EOF
```

Copy the full output (including `sha256=`).

### Step 3: Send Webhook Request

Replace `<SIGNATURE>` with your generated signature:

```bash
curl -X POST http://127.0.0.1:8000/v1/hooks/firecrawl-ingest \
  -H "Content-Type: application/json" \
  -H "X-Firecrawl-Signature: <SIGNATURE>" \
  --data-binary @test_firecrawl_payload.json
```

### Step 4: Confirm Success

Expected response:

```json
{
  "ok": true,
  "event_id": "evt_test_001",
  "type": "crawl.page",
  "processed": 1,
  "skipped_unchanged": 0
}
```

Server logs should include:
```
[RAG] Upsert <hash> url=https://vero.fi/tax-deduction company_id=company_123 source_id=vero
```

### Step 5: Verify Idempotency

Run the same curl command again. Expected response:

```json
{
  "ok": true,
  "deduped": true,
  "event_id": "evt_test_001",
  "type": "crawl.page"
}
```

## Verify Database Contents

```bash
sqlite3 local.db
```

Run queries:
```sql
SELECT company_id, source_id, url FROM documents;
SELECT event_id, event_type FROM firecrawl_events;
```

## Architecture

### Security & Isolation

- Tenant isolation enforced via `company_id` + `source_id`
- Webhook signature verification using `X-Firecrawl-Signature` header
- HMAC-SHA256 algorithm over raw request body

### Idempotency

- **Event-level dedupe**: Firecrawl retries are safe
- **Document-level dedupe**: Unchanged content is automatically skipped

### Database Schema

The backend uses SQLite locally (fast iteration) and can switch to Postgres without code changes.

#### Tables

**firecrawl_events**
- Stores every webhook event to prevent re-processing
- Fields: `event_id`, `event_type`, `raw_body_sha256`, `payload`
- Unique constraint: `(event_id, event_type)`

**documents**
- Stores the latest version of each page
- Unique per `{company_id, source_id, url}`
- `doc_key = sha256(company_id|source_id|url)`
- `content_hash = sha256(markdown)`
- Content stored as JSON (Markdown + Metadata)

**ingestion_runs** (optional)
- Logical grouping by `crawl_job_id` for debugging and observability

## Project Structure

```
firecrawl-backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── security.py
│   ├── schemas.py
│   ├── rag_pipeline.py
│   └── routes/
│       └── firecrawl_webhook.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Firecrawl Integration Notes

**This backend does not crawl by itself.** Crawling will be added later using the Firecrawl API key.

When integrated, Firecrawl cloud will:
- Crawl websites
- Convert pages to Markdown
- Send signed per-page webhooks to this service

This backend is ready for that integration.

## Status

| Feature | Status |
|---------|--------|
| Webhook ingestion | ✅ |
| Signature verification | ✅ |
| Idempotency | ✅ |
| Tenant isolation | ✅ |
| RAG handoff | ✅ |