from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class FirecrawlDocMetadata(BaseModel):
    source_url: Optional[str] = None
    title: Optional[str] = None
    # keep flexible for other fields
    extra: Dict[str, Any] = Field(default_factory=dict)


class FirecrawlDocument(BaseModel):
    markdown: Optional[str] = None
    html: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # Firecrawl returns metadata object


class FirecrawlWebhookEvent(BaseModel):
    success: bool = True
    type: str
    id: str
    data: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
