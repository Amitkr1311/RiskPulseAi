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
        "Amount,Category,Merchant,Recurring\n"
        "10000,Salary,Employer,yes\n"
        "2500,Food,Market,no\n"
        "1800,Travel,FX forward,no\n"
        "1200,Fixed Income,Corporate bond,no\n",
        encoding="utf-8",
    )

    positions = build_portfolio_module.build_portfolio(input_path, output_path)

    assert output_path.is_file()
    assert {position["asset_type"] for position in positions} == {
        "corporate_loan",
        "equity",
        "derivative",
        "corporate_bond",
    }
    assert all(Decimal(position["market_value"]) > 0 for position in positions)


def test_build_portfolio_reports_missing_input_without_creating_output(tmp_path):
    output_path = tmp_path / "portfolio_seed.json"

    with pytest.raises(FileNotFoundError, match="Download a permitted"):
        build_portfolio_module.build_portfolio(tmp_path / "missing.csv", output_path)

    assert not output_path.exists()
