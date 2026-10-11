"""Build the RiskPulse portfolio seed from a real transaction export.

The script intentionally does not ship or invent a transaction dataset. Pass a
Salad Money or Kaggle Financial Transactions CSV with ``--input``. Common
column names are supported; the output remains compatible with the backend
seed validator.
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "transactions.csv"
DEFAULT_OUTPUT = ROOT / "backend" / "data" / "portfolio_seed.json"

AMOUNT_COLUMNS = ("amount", "transaction_amount", "value", "debit", "credit")
CATEGORY_COLUMNS = ("category", "transaction_category", "merchant_category", "type")
MERCHANT_COLUMNS = ("merchant", "merchant_name", "merchant_type", "description", "payee")
RECURRING_COLUMNS = ("recurring", "is_recurring", "frequency")


def _column(field_map: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    return next((field_map[name] for name in candidates if name in field_map), None)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _amount(value: object) -> Decimal:
    raw = _clean(value).replace(",", "").replace("₹", "").replace("$", "")
    if raw.startswith("(") and raw.endswith(")"):
        raw = f"-{raw[1:-1]}"
    try:
        return abs(Decimal(raw))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"transaction amount is not numeric: {value!r}") from exc


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return result or "unclassified"


def _sector(category: str, merchant: str) -> str:
    text = f"{category} {merchant}".casefold()
    for terms, sector in (
        (("food", "grocery", "supermarket"), "consumer_staples"),
        (("utility", "electric", "water", "telecom"), "utilities"),
        (("transport", "fuel", "travel", "airline"), "transportation"),
        (("health", "medical", "pharmacy"), "healthcare"),
        (("technology", "software", "internet"), "technology"),
        (("bank", "finance", "insurance"), "financials"),
    ):
        if any(term in text for term in terms):
            return sector
    return "diversified"


def _parameterized_position(
    *, key: str, name: str, asset_type: str, value: Decimal, sector: str
) -> dict[str, Any]:
    common = {
        "position_key": key,
        "name": name,
        "asset_type": asset_type,
        "market_value": f"{value:.2f}",
        "currency": "INR",
        "sector": sector,
        "borrower": None,
    }
    if asset_type == "corporate_loan":
        common["borrower"] = "Transaction-derived recurring borrower group"
        common["valuation_parameters"] = {
            "basis": "exposure",
            "borrower_group_id": key,
            "sector": sector,
            "pd": "0.025",
            "lgd": "0.60",
            "recovery_rate": "0.40",
            "remaining_tenor_years": "3.0",
        }
    elif asset_type == "government_bond":
        common["borrower"] = "Government of India"
        common["valuation_parameters"] = {
            "basis": "market_value",
            "issuer": "Government of India",
            "maturity_year": 2032,
            "modified_duration": "6.0",
            "convexity": "42.0",
            "baseline_yield": "0.0715",
            "yield_unit": "decimal_rate",
        }
    elif asset_type == "corporate_bond":
        common["borrower"] = "Transaction-derived corporate issuers"
        common["valuation_parameters"] = {
            "basis": "market_value",
            "issuer": "Transaction-derived corporate issuers",
            "sector": sector,
            "credit_rating": "AA",
            "modified_duration": "4.0",
            "convexity": "22.0",
            "credit_spread_duration": "3.5",
            "baseline_credit_spread": "0.0180",
            "spread_unit": "decimal_rate",
        }
    elif asset_type == "derivative":
        common["valuation_parameters"] = {
            "basis": "simplified_mark_to_market",
            "instrument_type": "fx_forward",
            "derivative_kind": "fx_forward",
            "underlying": "USDINR",
            "notional_exposure_inr": f"{value * Decimal('2'):.2f}",
            "notional_currency": "USD",
            "tenor_years": "1.0",
            "fx_pair": "USDINR",
            "forward_fx_rate": "83.50",
            "spot_fx_rate": "82.50",
            "market_value_definition": "simplified_mark_to_market_portfolio_value",
        }
    else:
        common["valuation_parameters"] = {
            "basis": "market_value",
            "ticker": f"TXN{_slug(sector)[:8].upper()}",
            "instrument_name": f"Transaction-derived {sector} equity basket",
            "sector": sector,
            "beta": "1.00",
            "market_reference": "transaction-derived sector exposure",
        }
    return common


def read_transaction_groups(input_path: Path) -> list[dict[str, Any]]:
    if not input_path.is_file():
        raise FileNotFoundError(
            f"Transaction CSV not found: {input_path}. Download a permitted Salad Money or "
            "Kaggle Financial Transactions CSV and pass its path with --input."
        )
    with input_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        field_map = {
            field.strip().casefold(): field
            for field in (reader.fieldnames or [])
            if isinstance(field, str) and field.strip()
        }
        amount_column = _column(field_map, AMOUNT_COLUMNS)
        if amount_column is None:
            raise ValueError("Transaction CSV needs an Amount, Transaction Amount, Value, Debit, or Credit column")
        category_column = _column(field_map, CATEGORY_COLUMNS)
        merchant_column = _column(field_map, MERCHANT_COLUMNS)
        recurring_column = _column(field_map, RECURRING_COLUMNS)

        grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {"total": Decimal("0"), "count": 0, "recurring_count": 0}
        )
        for row_number, row in enumerate(reader, start=2):
            values = {
                key.casefold(): value.strip() if isinstance(value, str) else value
                for key, value in row.items()
                if isinstance(key, str)
            }
            category = _clean(values.get(category_column.casefold() if category_column else "")) or "unclassified"
            merchant = _clean(values.get(merchant_column.casefold() if merchant_column else "")) or "unknown merchant"
            key = (category.casefold(), merchant.casefold())
            group = grouped[key]
            group["category"] = category
            group["merchant"] = merchant
            group["total"] += _amount(values.get(amount_column.casefold()))
            group["count"] += 1
            recurring_value = _clean(values.get(recurring_column.casefold() if recurring_column else "")).casefold()
            if recurring_value in {"true", "yes", "y", "recurring", "monthly", "weekly"}:
                group["recurring_count"] += 1
    return list(grouped.values())


def build_portfolio(input_path: Path, output_path: Path) -> list[dict[str, Any]]:
    groups = read_transaction_groups(input_path)
    if not groups or sum((group["total"] for group in groups), Decimal("0")) <= 0:
        raise ValueError("Transaction CSV did not contain any positive monetary values")

    recurring_threshold = max((group["total"] for group in groups), default=Decimal("0")) * Decimal("0.10")
    fallback_assets = ["equity", "corporate_bond", "derivative"]
    fallback_index = 0
    positions: list[dict[str, Any]] = []
    for group in sorted(groups, key=lambda item: (-item["total"], item["category"], item["merchant"])):
        category = group["category"]
        merchant = group["merchant"]
        text = f"{category} {merchant}".casefold()
        recurring = group["recurring_count"] > 0 or group["count"] >= 2
        if any(term in text for term in ("loan", "mortgage", "credit")) or (
            recurring and group["total"] >= recurring_threshold
        ):
            asset_type = "corporate_loan"
        elif any(term in text for term in ("government bond", "treasury", "gilt")):
            asset_type = "government_bond"
        elif any(term in text for term in ("bond", "fixed income")):
            asset_type = "corporate_bond"
        elif any(term in text for term in ("derivative", "forward", "swap", "forex", "fx")):
            asset_type = "derivative"
        else:
            asset_type = fallback_assets[fallback_index % len(fallback_assets)]
            fallback_index += 1
        sector = _sector(category, merchant)
        key = f"txn_{_slug(category)}_{_slug(merchant)}"
        positions.append(
            _parameterized_position(
                key=key[:64],
                name=f"{category} / {merchant}",
                asset_type=asset_type,
                value=group["total"],
                sector=sector,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(positions, indent=2) + "\n", encoding="utf-8")
    return positions


def main() -> int:
    parser = argparse.ArgumentParser(description="Build backend/data/portfolio_seed.json from transactions")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="transaction CSV path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="portfolio seed JSON path")
    args = parser.parse_args()
    try:
        positions = build_portfolio(args.input.resolve(), args.output.resolve())
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Wrote {len(positions)} positions to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
