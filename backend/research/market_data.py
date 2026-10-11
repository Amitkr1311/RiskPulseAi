import csv
import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable

TICKER_PATTERN = re.compile(r"^[A-Za-z0-9.^_=-]{1,32}$")


class MarketDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class HistoricalPrice:
    trading_date: date
    close: float


@dataclass(frozen=True)
class HistoricalPriceSeries:
    symbol: str
    start: date
    end: date
    retrieved_at: datetime
    price_convention: str
    prices: tuple[HistoricalPrice, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "retrieved_at": self.retrieved_at.isoformat().replace("+00:00", "Z"),
            "price_convention": self.price_convention,
            "prices": [{"trading_date": item.trading_date.isoformat(), "close": item.close} for item in self.prices],
        }


def _as_date(value: date | str, name: str) -> date:
    if isinstance(value, datetime):
        return value.astimezone(UTC).date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise MarketDataError(f"{name} must be an ISO date") from exc


def _validate_request(symbol: str, start: date, end: date) -> None:
    if not TICKER_PATTERN.fullmatch(symbol.strip()):
        raise MarketDataError("symbol contains unsupported characters")
    if start >= end:
        raise MarketDataError("start must be earlier than end")


def _close_values(frame: Any) -> list[tuple[Any, Any]]:
    if frame is None or bool(getattr(frame, "empty", False)):
        return []
    for column in ("Close", "Adj Close"):
        try:
            series = frame[column]
        except (KeyError, TypeError, IndexError):
            continue
        if hasattr(series, "items"):
            return list(series.items())
    raise MarketDataError("market data response did not contain Close or Adj Close prices")


def _normalize_prices(values: list[tuple[Any, Any]]) -> tuple[HistoricalPrice, ...]:
    normalized: dict[date, float] = {}
    for raw_date, raw_value in values:
        try:
            timestamp = raw_date.to_pydatetime() if hasattr(raw_date, "to_pydatetime") else raw_date
            if isinstance(timestamp, datetime):
                trading_date = timestamp.astimezone(UTC).date() if timestamp.tzinfo else timestamp.date()
            elif isinstance(timestamp, date):
                trading_date = timestamp
            else:
                trading_date = date.fromisoformat(str(timestamp)[:10])
            close = float(raw_value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise MarketDataError("market data contains an invalid price or date") from exc
        if not math.isfinite(close) or close <= 0:
            continue
        normalized[trading_date] = close
    return tuple(HistoricalPrice(trading_date, normalized[trading_date]) for trading_date in sorted(normalized))


def download_historical_prices(
    symbol: str,
    start: date | str,
    end: date | str,
    *,
    downloader: Callable[..., Any] | None = None,
    timeout_seconds: float = 10.0,
) -> HistoricalPriceSeries:
    normalized_symbol = symbol.strip()
    start_date = _as_date(start, "start")
    end_date = _as_date(end, "end")
    _validate_request(normalized_symbol, start_date, end_date)
    if downloader is None:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise MarketDataError("yfinance is not installed; install backend/requirements.txt before using market research") from exc
        downloader = yf.download
    try:
        try:
            frame = downloader(
                normalized_symbol,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                auto_adjust=True,
                actions=False,
                progress=False,
                timeout=timeout_seconds,
                multi_level_index=False,
            )
        except TypeError as exc:
            if "multi_level_index" not in str(exc):
                raise
            frame = downloader(
                normalized_symbol,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                auto_adjust=True,
                actions=False,
                progress=False,
                timeout=timeout_seconds,
            )
    except Exception as exc:
        raise MarketDataError(f"historical market-data download failed for {normalized_symbol}") from exc
    prices = _normalize_prices(_close_values(frame))
    if not prices:
        raise MarketDataError(f"no valid historical prices returned for {normalized_symbol}")
    return HistoricalPriceSeries(
        symbol=normalized_symbol,
        start=start_date,
        end=end_date,
        retrieved_at=datetime.now(UTC),
        price_convention="daily close with yfinance auto_adjust=True",
        prices=prices,
    )


def export_prices_csv(series: HistoricalPriceSeries, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["symbol", "trading_date", "close", "price_convention"])
        writer.writeheader()
        for item in series.prices:
            writer.writerow({"symbol": series.symbol, "trading_date": item.trading_date.isoformat(), "close": item.close, "price_convention": series.price_convention})
    return path
