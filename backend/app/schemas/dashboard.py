from datetime import datetime

from pydantic import BaseModel, Field


class RecentSignalCounts(BaseModel):
    last_24_hours: int = Field(ge=0)
    last_7_days: int = Field(ge=0)
    last_30_days: int = Field(ge=0)


class DashboardSummary(BaseModel):
    total_articles: int = Field(ge=0)
    processed_articles: int = Field(ge=0)
    pending_articles: int = Field(ge=0)
    failed_articles: int = Field(ge=0)
    total_signals: int = Field(ge=0)
    high_impact_signals: int = Field(ge=0)
    high_impact_threshold: int = Field(ge=1, le=10)
    recent_signal_counts: RecentSignalCounts
    live_articles: int = Field(ge=0)
    demo_articles: int = Field(ge=0)
    latest_ingestion_at: datetime | None
    latest_processed_at: datetime | None
