from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    external_id: str | None
    title: str
    text: str
    url: str | None
    published_at: datetime | None
    ingested_at: datetime
    content_hash: str
    is_demo: bool
    is_historical: bool
    source_metadata: dict[str, object] | None
    processing_status: str
    processing_error: str | None
    processing_attempts: int
    processed_at: datetime | None


class ArticlePage(BaseModel):
    items: list[ArticleRead]
    total: int
    limit: int
    offset: int
