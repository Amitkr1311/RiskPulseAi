from decimal import Decimal

from app.db.models import PortfolioPosition, StressScenario


def test_foundation_models_are_importable_and_portfolio_total_is_reconciled(db_session):
    positions = [
        PortfolioPosition(
            name="Loans",
            asset_type="corporate_loan",
            market_value=Decimal("400000000.00"),
            currency="INR",
            valuation_parameters={"basis": "exposure"},
        ),
        PortfolioPosition(
            name="Bonds",
            asset_type="government_bond",
            market_value=Decimal("250000000.00"),
            currency="INR",
            valuation_parameters={"basis": "market_value"},
        ),
        PortfolioPosition(
            name="Corporate bonds",
            asset_type="corporate_bond",
            market_value=Decimal("200000000.00"),
            currency="INR",
            valuation_parameters={"basis": "market_value"},
        ),
        PortfolioPosition(
            name="Equities",
            asset_type="equity",
            market_value=Decimal("100000000.00"),
            currency="INR",
            valuation_parameters={"basis": "market_value"},
        ),
        PortfolioPosition(
            name="Derivatives",
            asset_type="derivative",
            market_value=Decimal("50000000.00"),
            currency="INR",
            valuation_parameters={"basis": "simplified_exposure"},
        ),
    ]
    scenario = StressScenario(
        name="Foundation scenario",
        event_category="market_crash",
        trigger_threshold=8,
        shock_parameters={"status": "foundation_only"},
        version="1.0",
        assumptions="No calculations in Milestone 1.",
    )
    db_session.add_all([*positions, scenario])
    db_session.commit()

    assert sum(position.market_value for position in positions) == Decimal("1000000000.00")
    assert scenario.event_category == "market_crash"

