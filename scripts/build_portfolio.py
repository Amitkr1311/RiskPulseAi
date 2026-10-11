"""Build the deterministic synthetic portfolio from a transaction export.

Transactions are consumer-activity evidence, not wholesale loan, bond, equity,
or derivative holdings. The builder therefore uses transaction categories only
to derive sector/recurring proxies and keeps the specification's required
₹100-crore asset mix as clearly labelled synthetic positions.
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "transactions.csv"
DEFAULT_OUTPUT = ROOT / "backend" / "data" / "portfolio_seed.json"
PORTFOLIO_TOTAL = Decimal("1000000000.00")

AMOUNT_COLUMNS = ("amount", "transaction_amount", "value", "debit", "credit")
CATEGORY_COLUMNS = ("category", "transaction_category", "merchant_category", "type")
MERCHANT_COLUMNS = ("merchant", "merchant_name", "merchant_type", "description", "payee")
RECURRING_COLUMNS = ("recurring", "is_recurring", "frequency")
DATE_COLUMNS = ("date", "transaction_date", "datetime", "timestamp")
TRANSACTION_TYPE_COLUMNS = ("transaction type", "transaction_type", "direction", "type")


def _column(field_map: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    return next((field_map[name] for name in candidates if name in field_map), None)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _parse_date(value: object, row_number: int) -> None:
    raw = _clean(value)
    if not raw:
        return
    for date_format in (
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            datetime.strptime(raw, date_format)
            return
        except ValueError:
            continue
    raise ValueError(f"transaction date is invalid on row {row_number}: {raw!r}")


def _amount(value: object, row_number: int) -> Decimal:
    raw = _clean(value).replace(",", "").replace("₹", "").replace("$", "")
    if raw.startswith("(") and raw.endswith(")"):
        raw = f"-{raw[1:-1]}"
    try:
        amount = abs(Decimal(raw))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"transaction amount is invalid on row {row_number}: {value!r}") from exc
    if amount <= 0:
        raise ValueError(f"transaction amount must be positive on row {row_number}")
    return amount


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return result or "unclassified"


def _sector(category: str, merchant: str) -> str:
    text = f"{category} {merchant}".casefold()
    for terms, sector in (
        (("food", "grocery", "supermarket", "restaurant", "coffee"), "consumer_staples"),
        (("utility", "electric", "water", "telecom", "internet", "mobile"), "utilities"),
        (("transport", "fuel", "travel", "airline", "auto"), "transportation"),
        (("health", "medical", "pharmacy"), "healthcare"),
        (("technology", "software", "internet", "electronics"), "technology"),
        (("bank", "finance", "insurance", "mortgage", "credit"), "financials"),
        (("home", "hardware", "improvement"), "real_estate_services"),
    ):
        if any(term in text for term in terms):
            return sector
    return "diversified"


def read_transaction_groups(input_path: Path) -> list[dict[str, Any]]:
    """Read validated debit groups and skip exact duplicate rows once."""

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Transaction CSV not found: {input_path}. Download a permitted transaction CSV and pass its path with --input."
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
        date_column = _column(field_map, DATE_COLUMNS)
        transaction_type_column = _column(field_map, TRANSACTION_TYPE_COLUMNS)

        grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {"total": Decimal("0"), "count": 0, "recurring_count": 0}
        )
        seen_rows: set[tuple[str, ...]] = set()
        for row_number, row in enumerate(reader, start=2):
            values = {
                key.casefold(): value.strip() if isinstance(value, str) else value
                for key, value in row.items()
                if isinstance(key, str)
            }
            fingerprint = tuple(_clean(values.get(field.casefold())) for field in field_map.values())
            if fingerprint in seen_rows:
                continue
            seen_rows.add(fingerprint)

            transaction_type = _clean(values.get(transaction_type_column.casefold() if transaction_type_column else "")).casefold()
            if transaction_type and transaction_type not in {"debit", "expense", "withdrawal", "purchase"}:
                # Credits such as paychecks are not spending exposure proxies.
                continue
            if date_column:
                _parse_date(values.get(date_column.casefold()), row_number)
            amount = _amount(values.get(amount_column.casefold()), row_number)
            category = _clean(values.get(category_column.casefold() if category_column else "")) or "unclassified"
            merchant = _clean(values.get(merchant_column.casefold() if merchant_column else "")) or "unknown merchant"
            key = (category.casefold(), merchant.casefold())
            group = grouped[key]
            group["category"] = category
            group["merchant"] = merchant
            group["total"] += amount
            group["count"] += 1
            recurring_value = _clean(values.get(recurring_column.casefold() if recurring_column else "")).casefold()
            if recurring_value in {"true", "yes", "y", "recurring", "monthly", "weekly"}:
                group["recurring_count"] += 1

    if not grouped:
        raise ValueError("Transaction CSV did not contain any valid debit transactions")
    return list(grouped.values())


def _profile(groups: list[dict[str, Any]]) -> dict[str, Any]:
    sector_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    recurring_groups = []
    for group in groups:
        sector = _sector(group["category"], group["merchant"])
        sector_totals[sector] += group["total"]
        if group["recurring_count"] > 0 or group["count"] >= 2:
            recurring_groups.append(group)
    sectors = sorted(sector_totals, key=lambda key: (-sector_totals[key], key))
    primary = sectors[0] if sectors else "diversified"
    secondary = sectors[1] if len(sectors) > 1 else primary
    recurring_sector = max(
        recurring_groups,
        key=lambda group: (group["total"], group["category"], group["merchant"]),
        default=None,
    )
    return {
        "primary_sector": primary,
        "secondary_sector": secondary,
        "recurring_sector": _sector(recurring_sector["category"], recurring_sector["merchant"])
        if recurring_sector
        else primary,
        "sector_totals": {key: f"{value:.2f}" for key, value in sorted(sector_totals.items())},
    }


def _position(*, key: str, name: str, asset_type: str, value: str, sector: str, borrower: str | None, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "position_key": key,
        "name": name,
        "asset_type": asset_type,
        "market_value": value,
        "currency": "INR",
        "sector": sector,
        "borrower": borrower,
        "valuation_parameters": parameters,
    }


def build_portfolio(input_path: Path, output_path: Path) -> list[dict[str, Any]]:
    groups = read_transaction_groups(input_path)
    profile = _profile(groups)
    positions = [
        _position(
            key="corporate_loans",
            name="Synthetic loan exposure proxy (recurring transactions)",
            asset_type="corporate_loan",
            value="400000000.00",
            sector=profile["recurring_sector"],
            borrower="Synthetic proxy; not transaction-level loan data",
            parameters={
                "basis": "exposure",
                "borrower_group_id": "synthetic-borrower-group",
                "sector": profile["recurring_sector"],
                "pd": "0.025",
                "lgd": "0.60",
                "recovery_rate": "0.40",
                "remaining_tenor_years": "3.0",
            },
        ),
        _position(
            key="government_bonds",
            name="Synthetic government bond allocation",
            asset_type="government_bond",
            value="250000000.00",
            sector="sovereign",
            borrower="Synthetic allocation; no transaction-level bond holding",
            parameters={
                "basis": "market_value",
                "issuer": "Government of India",
                "maturity_year": 2032,
                "modified_duration": "6.0",
                "convexity": "42.0",
                "baseline_yield": "0.0715",
                "yield_unit": "decimal_rate",
            },
        ),
        _position(
            key="corporate_bonds",
            name="Synthetic corporate bond allocation",
            asset_type="corporate_bond",
            value="200000000.00",
            sector=profile["secondary_sector"],
            borrower="Synthetic allocation; no transaction-level bond holding",
            parameters={
                "basis": "market_value",
                "issuer": "Synthetic Investment Grade Issuer",
                "sector": profile["secondary_sector"],
                "credit_rating": "AA",
                "modified_duration": "4.0",
                "convexity": "22.0",
                "credit_spread_duration": "3.5",
                "baseline_credit_spread": "0.0180",
                "spread_unit": "decimal_rate",
            },
        ),
        _position(
            key="equities",
            name="Synthetic equity sector allocation",
            asset_type="equity",
            value="100000000.00",
            sector=profile["primary_sector"],
            borrower=None,
            parameters={
                "basis": "market_value",
                "ticker": "SYNSECTOR",
                "instrument_name": "Synthetic sector basket informed by transaction categories",
                "sector": profile["primary_sector"],
                "beta": "1.10",
                "market_reference": "transaction-category mix; not a reported holding",
            },
        ),
        _position(
            key="irs_5y",
            name="Synthetic 5Y INR interest-rate swap",
            asset_type="derivative",
            value="15000000.00",
            sector="fixed_income",
            borrower=None,
            parameters={
                "basis": "simplified_mark_to_market",
                "instrument_type": "interest_rate_swap",
                "derivative_kind": "interest_rate_swap",
                "underlying": "INR benchmark rate",
                "notional_exposure_inr": "200000000.00",
                "tenor_years": "5.0",
                "duration_years": "5.0",
                "fixed_rate": "0.0725",
                "floating_rate": "0.0710",
                "rate_unit": "decimal_rate",
                "pay_receive": "pay_fixed",
                "market_value_definition": "simplified_mark_to_market_portfolio_value",
            },
        ),
        _position(
            key="irs_10y",
            name="Synthetic 10Y INR interest-rate swap",
            asset_type="derivative",
            value="10000000.00",
            sector="fixed_income",
            borrower=None,
            parameters={
                "basis": "simplified_mark_to_market",
                "instrument_type": "interest_rate_swap",
                "derivative_kind": "interest_rate_swap",
                "underlying": "INR benchmark rate",
                "notional_exposure_inr": "120000000.00",
                "tenor_years": "10.0",
                "duration_years": "8.0",
                "fixed_rate": "0.0750",
                "floating_rate": "0.0710",
                "rate_unit": "decimal_rate",
                "pay_receive": "pay_fixed",
                "market_value_definition": "simplified_mark_to_market_portfolio_value",
            },
        ),
        _position(
            key="fx_forward_usdinr",
            name="Synthetic USD/INR FX forward",
            asset_type="derivative",
            value="15000000.00",
            sector="foreign_exchange",
            borrower=None,
            parameters={
                "basis": "simplified_mark_to_market",
                "instrument_type": "fx_forward",
                "derivative_kind": "fx_forward",
                "underlying": "USDINR",
                "notional_exposure_inr": "150000000.00",
                "notional_currency": "USD",
                "tenor_years": "1.0",
                "fx_pair": "USDINR",
                "forward_fx_rate": "83.50",
                "spot_fx_rate": "82.50",
                "market_value_definition": "simplified_mark_to_market_portfolio_value",
            },
        ),
        _position(
            key="fx_forward_eurinr",
            name="Synthetic EUR/INR FX forward",
            asset_type="derivative",
            value="10000000.00",
            sector="foreign_exchange",
            borrower=None,
            parameters={
                "basis": "simplified_mark_to_market",
                "instrument_type": "fx_forward",
                "derivative_kind": "fx_forward",
                "underlying": "EURINR",
                "notional_exposure_inr": "100000000.00",
                "notional_currency": "EUR",
                "tenor_years": "0.75",
                "fx_pair": "EURINR",
                "forward_fx_rate": "91.00",
                "spot_fx_rate": "90.00",
                "market_value_definition": "simplified_mark_to_market_portfolio_value",
            },
        ),
    ]
    total = sum((Decimal(position["market_value"]) for position in positions), Decimal("0"))
    if total != PORTFOLIO_TOTAL:
        raise ValueError(f"Generated portfolio does not reconcile: {total} != {PORTFOLIO_TOTAL}")
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
    print(f"Wrote {len(positions)} synthetic positions to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
