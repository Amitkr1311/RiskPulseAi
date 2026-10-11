import json
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import Settings, get_settings
from app.schemas.research import (
    EventWindowRead,
    EventWindowResearchResponse,
    MarketPriceRead,
    MarketResearchResponse,
    SentimentEvaluationResponse,
)
from research.event_windows import analyze_event_window
from research.market_data import MarketDataError, download_historical_prices

router = APIRouter(prefix="/research", tags=["research"])


def _backend_path(settings: Settings, configured: str) -> Path:
    path = Path(configured)
    return path if path.is_absolute() else Path(__file__).resolve().parents[2] / path


def _series_read(series) -> MarketResearchResponse:
    return MarketResearchResponse(
        symbol=series.symbol,
        start=series.start.isoformat(),
        end=series.end.isoformat(),
        retrieved_at=series.retrieved_at,
        price_convention=series.price_convention,
        prices=[MarketPriceRead(trading_date=item.trading_date.isoformat(), close=item.close) for item in series.prices],
    )


@router.get("/sentiment-evaluation", response_model=SentimentEvaluationResponse)
def sentiment_evaluation(settings: Settings = Depends(get_settings)) -> SentimentEvaluationResponse:
    report_path = _backend_path(settings, settings.research_reports_dir) / "financial_phrasebank_latest.json"
    if not report_path.exists():
        return SentimentEvaluationResponse(
            available=False,
            message="No evaluation report is available. Run research.evaluate_sentiment to generate one.",
        )
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Evaluation report is unreadable") from exc
    if not isinstance(report, dict):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Evaluation report is invalid")
    return SentimentEvaluationResponse(available=True, report=report, message="Evaluation report loaded from local research output.")


@router.get("/market-data", response_model=MarketResearchResponse)
def market_data(
    symbol: str = Query(min_length=1, max_length=32),
    start: date = Query(),
    end: date = Query(),
) -> MarketResearchResponse:
    try:
        return _series_read(download_historical_prices(symbol, start, end))
    except MarketDataError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/event-window", response_model=EventWindowResearchResponse)
def event_window(
    symbol: str = Query(min_length=1, max_length=32),
    start: date = Query(),
    end: date = Query(),
    event_date: str = Query(min_length=1),
    event_category: str = Query(min_length=1, max_length=64),
    scenario_name: str = Query(min_length=1, max_length=255),
    assumed_shock: float = Query(gt=-1, lt=1),
    windows: str = Query(default="1,5,20"),
) -> EventWindowResearchResponse:
    try:
        window_values = tuple(int(value.strip()) for value in windows.split(",") if value.strip())
        series = download_historical_prices(symbol, start, end)
        observations = analyze_event_window(
            series,
            event_date,
            event_category=event_category,
            scenario_name=scenario_name,
            assumed_shock=assumed_shock,
            windows=window_values,
        )
    except (MarketDataError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return EventWindowResearchResponse(
        series=_series_read(series),
        observations=[EventWindowRead(**observation.to_dict()) for observation in observations],
        limitations=[
            "Observed returns and assumed stress shocks are displayed separately and are not causal evidence.",
            "Overlapping events, confounding factors, market regime changes, and proxy mismatch limit interpretation.",
            "Historical equity or index prices do not validate credit PD, LGD, duration, or derivatives pricing.",
        ],
    )
