from dataclasses import dataclass
from datetime import UTC, date, datetime

from research.market_data import HistoricalPriceSeries, MarketDataError


@dataclass(frozen=True)
class EventWindowObservation:
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

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "event_timestamp": self.event_timestamp,
            "event_date": self.event_date,
            "mapped_trading_date": self.mapped_trading_date,
            "mapping_policy": self.mapping_policy,
            "event_category": self.event_category,
            "scenario_name": self.scenario_name,
            "assumed_shock": self.assumed_shock,
            "window_trading_days": self.window_trading_days,
            "observation_date": self.observation_date,
            "observed_return": self.observed_return,
            "difference_observed_minus_assumed": self.difference_observed_minus_assumed,
        }


def _event_date(value: date | datetime | str) -> tuple[datetime, date]:
    if isinstance(value, datetime):
        timestamp = value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    else:
        try:
            timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise MarketDataError("event_date must be an ISO date or timestamp") from exc
        timestamp = timestamp.astimezone(UTC) if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
    return timestamp, timestamp.date()


def analyze_event_window(
    series: HistoricalPriceSeries,
    event_date: date | datetime | str,
    *,
    event_category: str,
    scenario_name: str,
    assumed_shock: float,
    windows: tuple[int, ...] = (1, 5, 20),
) -> list[EventWindowObservation]:
    if not windows or any(window < 1 for window in windows):
        raise MarketDataError("observation windows must contain positive trading-day counts")
    if not -1 < assumed_shock < 10:
        raise MarketDataError("assumed_shock must be a decimal return")
    timestamp, original_date = _event_date(event_date)
    prices = list(series.prices)
    mapped_index = next((index for index, price in enumerate(prices) if price.trading_date >= original_date), None)
    if mapped_index is None:
        raise MarketDataError("event date is after the available market-data period")
    mapped_price = prices[mapped_index]
    observations: list[EventWindowObservation] = []
    for window in windows:
        observation_index = mapped_index + window
        if observation_index >= len(prices):
            raise MarketDataError(f"not enough prices for a {window}-trading-day event window")
        observation = prices[observation_index]
        observed_return = observation.close / mapped_price.close - 1
        observations.append(
            EventWindowObservation(
                symbol=series.symbol,
                event_timestamp=timestamp.isoformat().replace("+00:00", "Z"),
                event_date=original_date.isoformat(),
                mapped_trading_date=mapped_price.trading_date.isoformat(),
                mapping_policy="same date or next available trading date",
                event_category=event_category,
                scenario_name=scenario_name,
                assumed_shock=assumed_shock,
                window_trading_days=window,
                observation_date=observation.trading_date.isoformat(),
                observed_return=observed_return,
                difference_observed_minus_assumed=observed_return - assumed_shock,
            )
        )
    return observations
