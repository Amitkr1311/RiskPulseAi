from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ReplayStatus = Literal["idle", "running", "paused", "completed", "stopped", "error"]


class ReplayStartRequest(BaseModel):
    speed_records_per_second: float = Field(default=1.0, gt=0, le=100)
    batch_size: int = Field(default=1, ge=1, le=100)


class ReplayStatusRead(BaseModel):
    dataset: str
    configured: bool
    status: ReplayStatus
    total_records: int
    records_attempted: int
    records_inserted: int
    duplicates_skipped: int
    records_failed: int
    current_position: int
    speed_records_per_second: float
    batch_size: int
    progress_percentage: float
    started_at: datetime | None
    last_record_at: datetime | None
    completed_at: datetime | None
    last_error: str | None
