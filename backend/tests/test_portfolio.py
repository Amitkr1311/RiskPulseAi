from decimal import Decimal

import pytest

from app.db.models import Portfolio, PortfolioPosition, StressScenario, StressTestResult, StressTestRun
from app.db.seed import seed_demo_portfolio
from app.portfolio.scenarios import SCENARIO_TEMPLATES
from app.schemas.portfolio import CorporateLoanParameters, GovernmentBondParameters
from app.services.portfolio import PortfolioService


def test_demo_seed_is_exact_and_idempotent(db_session) -> None:
    seed_demo_portfolio(db_session)
    db_session.commit()
    seed_demo_portfolio(db_session)
    db_session.commit()

    portfolio = db_session.query(Portfolio).one()
    assert len(portfolio.positions) == 20
    assert sum(position.market_value for position in portfolio.positions) == Decimal("1000000000.00")
    assert {position.asset_type for position in portfolio.positions} == {
        "corporate_loan",
        "government_bond",
        "corporate_bond",
        "equity",
        "derivative",
    }

    summary = PortfolioService(db_session).summary(portfolio.id)
    assert summary.total_market_value_inr == Decimal("1000000000.00")
    allocations = {item.asset_class: item.allocation_percentage for item in summary.asset_class_allocations}
    assert allocations == {
        "corporate_loan": Decimal("40.0"),
        "government_bond": Decimal("25.0"),
        "corporate_bond": Decimal("20.0"),
        "equity": Decimal("10.0"),
        "derivative": Decimal("5.0"),
    }


def test_demo_seed_replaces_the_legacy_single_derivative_book(db_session) -> None:
    portfolio = Portfolio(
        portfolio_key="demo-banking-portfolio",
        name="Demo Banking Portfolio",
        currency="INR",
        is_demo=True,
    )
    db_session.add(portfolio)
    db_session.flush()
    db_session.add(
        PortfolioPosition(
            portfolio_id=portfolio.id,
            position_key="derivatives",
            name="Derivative marked-to-market book",
            asset_type="derivative",
            market_value=Decimal("50000000"),
            currency="INR",
            is_demo=True,
            valuation_parameters={
                "basis": "simplified_mark_to_market",
                "instrument_type": "index_total_return_swap",
                "underlying": "SYNBANK",
                "notional_exposure_inr": "100000000",
                "delta_equivalent": "0.50",
                "market_value_definition": "simplified_mark_to_market_portfolio_value",
            },
        )
    )
    db_session.commit()

    seed_demo_portfolio(db_session)
    db_session.commit()

    assert db_session.query(PortfolioPosition).filter_by(portfolio_id=portfolio.id).count() == 20
    assert db_session.query(PortfolioPosition).filter_by(position_key="derivatives").count() == 0


def test_demo_seed_repoints_legacy_derivative_results_before_removal(db_session) -> None:
    portfolio = Portfolio(
        portfolio_key="demo-banking-portfolio",
        name="Demo Banking Portfolio",
        currency="INR",
        is_demo=True,
    )
    scenario = StressScenario(
        scenario_key="legacy-test",
        name="Legacy test scenario",
        event_category="market_crash",
        trigger_threshold=7,
        shock_parameters={},
        version="1.0",
        assumptions="Test scenario",
    )
    db_session.add_all([portfolio, scenario])
    db_session.flush()
    legacy = PortfolioPosition(
        portfolio_id=portfolio.id,
        position_key="derivatives",
        name="Derivative marked-to-market book",
        asset_type="derivative",
        market_value=Decimal("50000000"),
        currency="INR",
        is_demo=True,
        valuation_parameters={
            "basis": "simplified_mark_to_market",
            "instrument_type": "index_total_return_swap",
            "underlying": "SYNBANK",
            "notional_exposure_inr": "100000000",
            "delta_equivalent": "0.50",
            "market_value_definition": "simplified_mark_to_market_portfolio_value",
        },
    )
    db_session.add(legacy)
    db_session.flush()
    run = StressTestRun(
        trigger_key="legacy-result",
        portfolio_id=portfolio.id,
        scenario_id=scenario.id,
        portfolio_value_before=Decimal("1000000000"),
        portfolio_value_after=Decimal("995000000"),
        pnl=Decimal("-5000000"),
        loss_percentage=Decimal("0.5"),
        portfolio_return_percentage=Decimal("-0.5"),
        status="completed",
        trigger_mode="manual",
        scenario_version="1.0",
        model_version="stress-v1",
    )
    db_session.add(run)
    db_session.flush()
    result = StressTestResult(
        run_id=run.id,
        position_id=legacy.id,
        position_value_before=Decimal("50000000"),
        position_value_after=Decimal("47500000"),
        contribution=Decimal("-2500000"),
        position_key_snapshot="derivatives",
        position_name_snapshot="Derivative marked-to-market book",
        asset_type_snapshot="derivative",
        inclusion_status="included",
        calculation_method="legacy",
        explanation="Legacy test result",
        calculation_details={},
    )
    db_session.add(result)
    db_session.commit()

    seed_demo_portfolio(db_session)
    db_session.commit()

    replacement = db_session.query(PortfolioPosition).filter_by(position_key="irs_5y").one()
    assert db_session.get(StressTestResult, result.id).position_id == replacement.id
    assert db_session.query(PortfolioPosition).filter_by(position_key="derivatives").count() == 0


def test_zero_value_portfolio_is_safe(db_session) -> None:
    portfolio = Portfolio(
        portfolio_key="zero-portfolio",
        name="Zero Portfolio",
        currency="INR",
        is_demo=True,
    )
    db_session.add(portfolio)
    db_session.commit()
    summary = PortfolioService(db_session).summary(portfolio.id)
    assert summary.total_market_value_inr == Decimal("0")
    assert summary.position_count == 0
    assert summary.asset_class_allocations == []


def test_asset_parameter_validation_rejects_invalid_credit_and_duration_values() -> None:
    with pytest.raises(ValueError):
        CorporateLoanParameters(
            basis="exposure",
            borrower_group_id="borrower",
            sector="finance",
            pd=Decimal("1.01"),
            lgd=Decimal("0.60"),
            recovery_rate=Decimal("0.40"),
        )
    with pytest.raises(ValueError):
        CorporateLoanParameters(
            basis="exposure",
            borrower_group_id="borrower",
            sector="finance",
            pd=Decimal("0.02"),
            lgd=Decimal("0.60"),
            recovery_rate=Decimal("0.50"),
        )
    with pytest.raises(ValueError):
        GovernmentBondParameters(
            basis="market_value",
            issuer="Issuer",
            maturity_year=2030,
            modified_duration=Decimal("-1"),
            baseline_yield=Decimal("0.07"),
            yield_unit="decimal_rate",
        )


def test_scenario_templates_are_deterministic_and_units_are_explicit() -> None:
    assert {template.event_category for template in SCENARIO_TEMPLATES} == {
        "geopolitical",
        "macroeconomic",
        "credit_event",
        "regulatory",
        "market_crash",
    }
    assert all(template.version == "1.0" for template in SCENARIO_TEMPLATES)
    assert all(parameter.unit for template in SCENARIO_TEMPLATES for parameter in template.shock_parameters)


def test_portfolio_endpoints_return_explicit_units_and_filters(client, db_session) -> None:
    seed_demo_portfolio(db_session)
    db_session.commit()

    portfolio_response = client.get("/portfolio")
    assert portfolio_response.status_code == 200
    portfolio = portfolio_response.json()
    assert portfolio["total_market_value_inr"] == "1000000000.00"
    assert portfolio["total_market_value_crore"] == "100.00"
    assert portfolio["position_count"] == 20
    assert portfolio["is_demo"] is True

    positions_response = client.get("/portfolio/positions?asset_class=equity&limit=100")
    assert positions_response.status_code == 200
    body = positions_response.json()
    assert body["total"] == 5
    assert sum(Decimal(item["market_value_inr"]) for item in body["items"]) == Decimal("100000000.00")
    position_id = body["items"][0]["id"]

    detail_response = client.get(f"/portfolio/positions/{position_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["valuation_parameters"]["beta"] == "1.10"

    summary_response = client.get("/portfolio/summary")
    assert summary_response.status_code == 200
    assert Decimal(summary_response.json()["asset_class_allocations"][0]["allocation_percentage"]) in {
        Decimal("5"),
        Decimal("10"),
        Decimal("20"),
        Decimal("25"),
        Decimal("40"),
    }
    assert client.get("/portfolio/positions/999999").status_code == 404
    assert client.get("/portfolio/positions?asset_class=unknown").status_code == 422
