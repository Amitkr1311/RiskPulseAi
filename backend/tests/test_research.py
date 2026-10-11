from datetime import date, datetime

import pytest

from research.event_windows import analyze_event_window
from research.market_data import HistoricalPrice, MarketDataError, download_historical_prices, export_prices_csv
from research.metrics import MetricInputError, evaluate_predictions
from research.phrasebank import load_examples


class FakeFrame:
    empty = False

    def __init__(self, values):
        self.values = values

    def __getitem__(self, key):
        if key != "Close":
            raise KeyError(key)
        return self.values


def test_metrics_are_deterministic_and_report_per_class_values() -> None:
    report = evaluate_predictions(
        ["negative", "neutral", "positive", "positive"],
        ["negative", "positive", "positive", "neutral"],
    )
    assert report["evaluated_examples"] == 4
    assert report["accuracy"] == pytest.approx(0.5)
    assert report["confusion_matrix"]["positive"]["neutral"] == 1
    assert set(report["per_class"]) == {"negative", "neutral", "positive"}


def test_metrics_reject_empty_and_invalid_labels() -> None:
    with pytest.raises(MetricInputError):
        evaluate_predictions([], [])
    with pytest.raises(MetricInputError):
        evaluate_predictions(["negative"], ["unknown"])


def test_phrasebank_local_loader_maps_numeric_labels(tmp_path) -> None:
    path = tmp_path / "phrasebank.csv"
    path.write_text("sentence,label\nProfit increased,positive\nCosts fell,-1\nStable outlook,0\n", encoding="utf-8")
    examples = load_examples(local_path=str(path))
    assert [(example.sentence, example.label) for example in examples] == [
        ("Profit increased", "positive"),
        ("Costs fell", "negative"),
        ("Stable outlook", "neutral"),
    ]


def test_market_data_normalizes_duplicate_dates_and_exports_csv(tmp_path) -> None:
    frame = FakeFrame(
        {
            datetime(2024, 1, 2): 100,
            datetime(2024, 1, 2, 15): 101,
            datetime(2024, 1, 3): 102,
        }
    )
    series = download_historical_prices(
        "^GSPC",
        "2024-01-01",
        "2024-01-05",
        downloader=lambda *_args, **_kwargs: frame,
    )
    assert [price.close for price in series.prices] == [101.0, 102.0]
    output = export_prices_csv(series, tmp_path / "prices.csv")
    assert output.read_text(encoding="utf-8").count("^GSPC") == 2


def test_market_data_rejects_empty_results() -> None:
    with pytest.raises(MarketDataError, match="no valid"):
        download_historical_prices("^GSPC", date(2024, 1, 1), date(2024, 1, 5), downloader=lambda *_args, **_kwargs: FakeFrame({}))


def test_event_window_maps_weekend_to_next_trading_date() -> None:
    series = type("Series", (), {
        "symbol": "^GSPC",
        "prices": (
            HistoricalPrice(date(2024, 1, 5), 100),
            HistoricalPrice(date(2024, 1, 8), 102),
            HistoricalPrice(date(2024, 1, 9), 104),
            HistoricalPrice(date(2024, 1, 10), 103),
        ),
    })()
    observations = analyze_event_window(
        series,
        "2024-01-06T12:00:00Z",
        event_category="market_crash",
        scenario_name="Broad market crash",
        assumed_shock=-0.10,
        windows=(1,),
    )
    assert observations[0].mapped_trading_date == "2024-01-08"
    assert observations[0].observation_date == "2024-01-09"
    assert observations[0].observed_return == pytest.approx(104 / 102 - 1)
    assert observations[0].difference_observed_minus_assumed == pytest.approx(104 / 102 - 1 + 0.10)


def test_research_api_reports_unavailable_evaluation_without_fabricating_metrics(client) -> None:
    response = client.get("/research/sentiment-evaluation")
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["report"] is None
