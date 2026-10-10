from decimal import Decimal

from app.db.models import Portfolio, PortfolioPosition, StressScenario


def test_foundation_models_are_importable_and_portfolio_total_is_reconciled(db_session):
    portfolio = Portfolio(
        portfolio_key="foundation-test",
        name="Foundation Test Portfolio",
        currency="INR",
        is_demo=True,
    )
    positions = [
        PortfolioPosition(
            portfolio=portfolio,
            position_key="loans",
            name="Loans",
            asset_type="corporate_loan",
            market_value=Decimal("400000000.00"),
            currency="INR",
            valuation_parameters={"basis": "exposure"},
        ),
        PortfolioPosition(
            portfolio=portfolio,
            position_key="government_bonds",
            name="Bonds",
            asset_type="government_bond",
            market_value=Decimal("250000000.00"),
            currency="INR",
            valuation_parameters={"basis": "market_value"},
        ),
        PortfolioPosition(
            portfolio=portfolio,
            position_key="corporate_bonds",
            name="Corporate bonds",
            asset_type="corporate_bond",
            market_value=Decimal("200000000.00"),
            currency="INR",
            valuation_parameters={"basis": "market_value"},
        ),
        PortfolioPosition(
            portfolio=portfolio,
            position_key="equities",
            name="Equities",
            asset_type="equity",
            market_value=Decimal("100000000.00"),
            currency="INR",
            valuation_parameters={"basis": "market_value"},
        ),
        PortfolioPosition(
            portfolio=portfolio,
            position_key="derivatives",
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
    db_session.add_all([portfolio, *positions, scenario])
    db_session.commit()

    assert sum(position.market_value for position in positions) == Decimal("1000000000.00")
    assert scenario.event_category == "market_crash"
