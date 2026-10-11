from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SentimentEvaluationResponse(BaseModel):
    available: bool
    report: dict[str, Any] | None = None
    message: str


class MarketPriceRead(BaseModel):
    trading_date: str
    close: float


class MarketResearchResponse(BaseModel):
    symbol: str
    start: str
    end: str
    retrieved_at: datetime
    price_convention: str
    prices: list[MarketPriceRead]


class EventWindowRead(BaseModel):
    symbol: str
    event_timestamp: str
    event_date: str
    mapped_trading_date: str
    mapping_policy: str
    event_category: str
    scenario_name: str
    assumed_shock: float
    window_trading_days: int
    observation_date: str
    observed_return: float
    difference_observed_minus_assumed: float


class EventWindowResearchResponse(BaseModel):
    series: MarketResearchResponse
    observations: list[EventWindowRead]
    limitations: list[str]
