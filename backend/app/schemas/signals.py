from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.articles import ArticleRead


class EntitySignalRead(BaseModel):
    mention: str
    canonical_name: str
    identifier: str | None
    resolved: bool
    entity_type: str


class RiskSignalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    article_id: int
    source: str
    article_title: str
    article_url: str | None
    is_demo: bool
    article: ArticleRead
    entities: list[EntitySignalRead]
    sentiment_label: str | None
    sentiment_score: float
    sentiment_probabilities: dict[str, float] | None
    event_type: str
    event_confidence: float | None = Field(default=None, ge=0, le=1)
    impact_score: int = Field(ge=1, le=10)
    impact_factors: dict[str, Any] | None
    explanation: str
    model_version: str
    model_metadata: dict[str, Any] | None
    scoring_config_version: str
    created_at: datetime

    @field_validator("sentiment_score")
    @classmethod
    def validate_sentiment_score(cls, value: float) -> float:
        if not -1 <= value <= 1:
            raise ValueError("sentiment_score must be between -1 and 1")
        return value

    @field_validator("sentiment_probabilities")
    @classmethod
    def validate_probabilities(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        if value is not None and any(not 0 <= probability <= 1 for probability in value.values()):
            raise ValueError("sentiment probabilities must be between 0 and 1")
        return value


class SignalPage(BaseModel):
    items: list[RiskSignalRead]
    total: int
    limit: int
    offset: int


class ProcessRequest(BaseModel):
    limit: int = Field(default=25, ge=1, le=100)


class ProcessResponse(BaseModel):
    requested: int
    processed: int
    skipped: int
    failed: int
    results: list[dict[str, Any]]


class NLPStatus(BaseModel):
    sentiment_backend: str
    sentiment_model_id: str
    model_available: bool
    model_download_allowed: bool
    pending_articles: int
    failed_articles: int
    processed_articles: int
    signal_count: int
