import datetime as dt
from sqlalchemy import String, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON  # works on sqlite
from sqlalchemy.types import JSON

from .db import Base


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class FirecrawlEvent(Base):
    __tablename__ = "firecrawl_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)

    received_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    # for auditing/debugging
    signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    raw_body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    payload: Mapped[dict] = mapped_column(JSON().with_variant(SQLITE_JSON, "sqlite"), nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id", "event_type", name="uq_firecrawl_event"),
    )


class Document(Base):
    """
    Stores the latest content for a given (company_id, source_id, url).
    Overwrite latest; keep lightweight version metadata (hash, timestamps).
    """
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # deterministic key, used as stable identifier across overwrites
    doc_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    company_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256(markdown)
    content: Mapped[dict] = mapped_column(JSON().with_variant(SQLITE_JSON, "sqlite"), nullable=False)

    crawl_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
