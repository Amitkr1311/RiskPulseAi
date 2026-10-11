import importlib.util
from pathlib import Path
from decimal import Decimal

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_portfolio.py"
SPEC = importlib.util.spec_from_file_location("build_portfolio", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
build_portfolio_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_portfolio_module)


def test_build_portfolio_maps_transaction_groups_to_valid_position_shapes(tmp_path):
    input_path = tmp_path / "transactions.csv"
    output_path = tmp_path / "portfolio_seed.json"
    input_path.write_text(
        "Date,Amount,Category,Description,Transaction Type\n"
        "01/01/2018,10000,Salary,Employer,credit\n"
        "01/02/2018,2500,Food,Market,debit\n"
        "01/03/2018,1800,Travel,Taxi,debit\n"
        "01/04/2018,1200,Fixed Income,Corporate bond,debit\n"
        "01/04/2018,1200,Fixed Income,Corporate bond,debit\n",
        encoding="utf-8",
    )

    positions = build_portfolio_module.build_portfolio(input_path, output_path)

    assert output_path.is_file()
    assert {position["asset_type"] for position in positions} == {
        "corporate_loan", "government_bond", "corporate_bond", "equity", "derivative"
    }
    assert len(positions) == 8
    assert sum(Decimal(position["market_value"]) for position in positions) == Decimal("1000000000.00")
    assert all("Synthetic" in position["name"] for position in positions)
    assert positions[0]["valuation_parameters"]["basis"] == "exposure"
    assert all(Decimal(position["market_value"]) > 0 for position in positions)


def test_builder_rejects_invalid_amount_and_date(tmp_path):
    input_path = tmp_path / "bad.csv"
    output_path = tmp_path / "portfolio_seed.json"
    input_path.write_text(
        "Date,Amount,Category,Description,Transaction Type\n"
        "01/99/2018,nope,Food,Market,debit\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="transaction date is invalid"):
        build_portfolio_module.build_portfolio(input_path, output_path)


def test_builder_rejects_invalid_amount(tmp_path):
    input_path = tmp_path / "bad-amount.csv"
    input_path.write_text(
        "Date,Amount,Category,Description,Transaction Type\n"
        "01/01/2018,nope,Food,Market,debit\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="transaction amount is invalid"):
        build_portfolio_module.read_transaction_groups(input_path)


def test_builder_rejects_missing_amount_column(tmp_path):
    input_path = tmp_path / "bad.csv"
    input_path.write_text("Date,Category,Description\n01/01/2018,Food,Market\n", encoding="utf-8")

    with pytest.raises(ValueError, match="needs an Amount"):
        build_portfolio_module.read_transaction_groups(input_path)


def test_build_portfolio_reports_missing_input_without_creating_output(tmp_path):
    output_path = tmp_path / "portfolio_seed.json"

    with pytest.raises(FileNotFoundError, match="Download a permitted"):
        build_portfolio_module.build_portfolio(tmp_path / "missing.csv", output_path)

    assert not output_path.exists()
