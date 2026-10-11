import argparse
import json
from datetime import date
from pathlib import Path

from research.event_windows import analyze_event_window
from research.market_data import MarketDataError, download_historical_prices, export_prices_csv


def _date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve optional historical market research from yfinance")
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download", help="download daily adjusted historical prices")
    download.add_argument("--symbol", required=True)
    download.add_argument("--start", required=True)
    download.add_argument("--end", required=True)
    download.add_argument("--output", default="research/market_data/prices.csv")

    window = subparsers.add_parser("event-window", help="compare observed returns with an assumed scenario shock")
    window.add_argument("--symbol", required=True)
    window.add_argument("--start", required=True)
    window.add_argument("--end", required=True)
    window.add_argument("--event-date", required=True, help="ISO date or timestamp")
    window.add_argument("--event-category", required=True)
    window.add_argument("--scenario-name", required=True)
    window.add_argument("--assumed-shock", required=True, type=float)
    window.add_argument("--windows", default="1,5,20", help="comma-separated trading-day windows")
    window.add_argument("--output", default="research/market_data/event_window.json")
    window.add_argument("--prices-output", default="research/market_data/prices.csv")

    args = parser.parse_args()
    try:
        series = download_historical_prices(args.symbol, _date(args.start), _date(args.end))
        if args.command == "download":
            output = export_prices_csv(series, args.output)
            print(json.dumps({"series": series.to_dict(), "csv": str(output)}, indent=2))
            return 0

        windows = tuple(int(value.strip()) for value in args.windows.split(",") if value.strip())
        observations = analyze_event_window(
            series,
            args.event_date,
            event_category=args.event_category,
            scenario_name=args.scenario_name,
            assumed_shock=args.assumed_shock,
            windows=windows,
        )
        prices_output = export_prices_csv(series, args.prices_output)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "series": series.to_dict(),
                    "prices_csv": str(prices_output),
                    "observations": [observation.to_dict() for observation in observations],
                    "limitations": [
                        "Observed returns and assumed stress shocks are displayed separately and are not causal evidence.",
                        "Overlapping events, confounding factors, market regime changes, and proxy mismatch limit interpretation.",
                        "Historical equity or index prices do not validate credit PD, LGD, duration, or derivatives pricing.",
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(output.read_text(encoding="utf-8"))
        return 0
    except (MarketDataError, ValueError) as exc:
        print(f"MARKET RESEARCH FAILED: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
