import hmac
import hashlib
from fastapi import Header, HTTPException, Request
from .config import settings


async def verify_firecrawl_signature(
    request: Request,
    x_firecrawl_signature: str | None = Header(default=None, alias="X-Firecrawl-Signature"),
) -> bytes:
    if not x_firecrawl_signature:
        raise HTTPException(status_code=401, detail="Missing X-Firecrawl-Signature")

    # Expected format: "sha256=abc123..."
    try:
        prefix, provided_hex = x_firecrawl_signature.split("=", 1)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid signature format")

    if prefix.lower() != "sha256":
        raise HTTPException(status_code=401, detail="Unsupported signature prefix")

    raw_body = await request.body()

    computed = hmac.new(
        key=settings.FIRECRAWL_WEBHOOK_SECRET.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # timing-safe compare
    if not hmac.compare_digest(computed, provided_hex):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    return raw_body
