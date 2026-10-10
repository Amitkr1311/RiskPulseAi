from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SourceName = Literal["news", "reddit"]


class IngestionRunRequest(BaseModel):
    sources: list[SourceName] = Field(default_factory=lambda: ["news", "reddit"], min_length=1)
    limit: int = Field(default=25, ge=1, le=100)


class SourceRunSummary(BaseModel):
    run_id: int
    source: str
    status: str
    fetched: int
    inserted: int
    duplicates_skipped: int
    failed: int
    error_category: str | None = None


class IngestionResponse(BaseModel):
    runs: list[SourceRunSummary]
    fetched: int
    inserted: int
    duplicates_skipped: int
    failed: int


class IngestionRunRead(BaseModel):
    run_id: int
    source: str
    status: str
    records_seen: int
    records_created: int
    duplicates_skipped: int
    records_failed: int
    error_category: str | None
    started_at: datetime
    completed_at: datetime | None


class SourceStatus(BaseModel):
    source: str
    configured: bool
    last_run: IngestionRunRead | None = None


class IngestionStatusResponse(BaseModel):
    sources: list[SourceStatus]
    recent_runs: list[IngestionRunRead]

