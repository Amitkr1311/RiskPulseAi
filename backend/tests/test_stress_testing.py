from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.db.models import Article, Portfolio, RiskSignal, StressTestRun
from app.db.seed import seed_demo_portfolio, seed_scenarios
from app.schemas.portfolio import CorporateBondParameters, CorporateLoanParameters, DerivativeParameters, EquityParameters, GovernmentBondParameters
from app.nlp.service import NLPService
from app.stress_testing.calculations import corporate_bond_valuation, corporate_loan_valuation, derivative_valuation, equity_valuation, government_bond_valuation
from app.stress_testing.service import StressTestingService


def test_asset_calculations_use_documented_decimal_formulas() -> None:
    gov = government_bond_valuation(
        Decimal("100.00"),
        GovernmentBondParameters(basis="market_value", issuer="Gov", maturity_year=2032, modified_duration=Decimal("5"), baseline_yield=Decimal("0.07"), yield_unit="decimal_rate"),
        Decimal("100"),
    )
    assert gov.stressed_value == Decimal("95.00")
    assert gov.pnl == Decimal("-5.00")

    corporate = corporate_bond_valuation(
        Decimal("100.00"),
        CorporateBondParameters(basis="market_value", issuer="Issuer", sector="finance", credit_rating="AA", modified_duration=Decimal("4"), credit_spread_duration=Decimal("3.5"), baseline_credit_spread=Decimal("0.02"), spread_unit="decimal_rate"),
        Decimal("100"),
        Decimal("50"),
    )
    assert corporate.stressed_value == Decimal("94.25")

    loan = corporate_loan_valuation(
        Decimal("100.00"),
        CorporateLoanParameters(basis="exposure", borrower_group_id="borrower", sector="finance", pd=Decimal("0.10"), lgd=Decimal("0.50"), recovery_rate=Decimal("0.50")),
        Decimal("2"),
    )
    assert loan.details["stressed_pd"] == "0.20"
    assert loan.pnl == Decimal("-5.00")

    equity = equity_valuation(Decimal("100.00"), EquityParameters(basis="market_value", ticker="ABC", instrument_name="ABC", sector="finance", beta=Decimal("1.1")), Decimal("-0.20"))
    assert equity.stressed_value == Decimal("80.00")

    derivative = derivative_valuation(Decimal("100.00"), DerivativeParameters(basis="simplified_mark_to_market", instrument_type="swap", underlying="ABC", notional_exposure_inr=Decimal("1000"), delta_equivalent=Decimal("0.5"), market_value_definition="simplified_mark_to_market_portfolio_value"), Decimal("-0.20"))
    assert derivative.pnl == Decimal("-10.00")


def _seed_signal(db_session, *, event_type: str, impact_score: int, entity_name: str | None = None) -> RiskSignal:
    article = Article(source="demo", title=f"{event_type} article", text="Synthetic stress signal", content_hash=f"stress-{event_type}-{impact_score}-{entity_name}", is_demo=True, processing_status="processed")
    db_session.add(article)
    db_session.flush()
    signal = RiskSignal(article_id=article.id, entity_name=entity_name, sentiment_score=Decimal("-0.8"), event_type=event_type, impact_score=impact_score, explanation="Deterministic test signal", model_version="test-v1")
    db_session.add(signal)
    db_session.commit()
    return signal


def test_broad_market_run_is_deterministic_and_reconciles(db_session) -> None:
    portfolio = seed_demo_portfolio(db_session)
    seed_scenarios(db_session)
    signal = _seed_signal(db_session, event_type="market_crash", impact_score=9)

    service = StressTestingService(db_session, Settings())
    first, reused = service.run(portfolio_id=portfolio.id, scenario_id="broad_market_crash", risk_signal_id=signal.id, trigger_mode="automatic", fresh_run=False)
    second, reused_again = service.run(portfolio_id=portfolio.id, scenario_id="broad_market_crash", risk_signal_id=signal.id, trigger_mode="automatic", fresh_run=False)

    assert reused is False
    assert reused_again is True
    assert first.simulation_id == second.simulation_id
    assert first.portfolio_value_before == Decimal("1000000000.00")
    assert first.pnl == Decimal("-34368750.00")
    assert first.reconciliation.reconciled is True
    assert len(first.results) == 5


def test_high_impact_persisted_signal_automatically_runs_matching_scenario(db_session) -> None:
    portfolio = seed_demo_portfolio(db_session)
    seed_scenarios(db_session)
    article = Article(
        source="demo",
        title="War sanctions raise market risk",
        text="War and sanctions create a crisis with losses for financial markets.",
        content_hash="auto-trigger-geopolitical",
        is_demo=True,
        processing_status="pending",
    )
    db_session.add(article)
    db_session.commit()

    result = NLPService(db_session, Settings()).process_article(article.id)

    assert result.status == "processed"
    run = db_session.query(StressTestRun).one()
    assert run.portfolio_id == portfolio.id
    assert run.trigger_mode == "automatic"
    assert run.triggered_by_signal_id == result.signal_id
    assert run.trigger_signal_id == result.signal_id


def test_auto_trigger_uses_strictly_greater_than_threshold(db_session) -> None:
    portfolio = seed_demo_portfolio(db_session)
    seed_scenarios(db_session)
    signal = _seed_signal(db_session, event_type="market_crash", impact_score=7)

    triggered = StressTestingService(db_session, Settings()).auto_trigger_for_signal(
        signal.id, portfolio.id
    )

    assert triggered == []
    assert db_session.query(StressTestRun).count() == 0


def test_eligibility_threshold_mapping_and_relevance(db_session) -> None:
    portfolio = seed_demo_portfolio(db_session)
    seed_scenarios(db_session)
    service = StressTestingService(db_session, Settings())

    equal_signal = _seed_signal(db_session, event_type="market_crash", impact_score=7)
    equal_result = service.eligibility_for_signal(equal_signal.id, portfolio.id)
    assert equal_result.eligible is False
    assert "below_impact_threshold" in equal_result.reasons

    unsupported = _seed_signal(db_session, event_type="earnings", impact_score=9)
    unsupported_result = service.eligibility_for_signal(unsupported.id, portfolio.id)
    assert unsupported_result.eligible is False
    assert "unsupported_event_type" in unsupported_result.reasons

    targeted_missing = _seed_signal(db_session, event_type="credit_event", impact_score=9, entity_name="Unknown borrower")
    missing_result = service.eligibility_for_signal(targeted_missing.id, portfolio.id)
    assert missing_result.eligible is False
    assert "insufficient_portfolio_relevance" in missing_result.reasons

    targeted_match = _seed_signal(db_session, event_type="credit_event", impact_score=9, entity_name="synthetic-borrower-group")
    match_result = service.eligibility_for_signal(targeted_match.id, portfolio.id)
    assert match_result.eligible is True
    assert match_result.matching_scenarios == ["credit_deterioration"]


def test_stress_api_lists_runs_and_rejects_ineligible_signal(client, db_session) -> None:
    portfolio = seed_demo_portfolio(db_session)
    seed_scenarios(db_session)
    signal = _seed_signal(db_session, event_type="market_crash", impact_score=9)

    scenarios = client.get("/stress-testing/scenarios")
    assert scenarios.status_code == 200
    assert {item["scenario_id"] for item in scenarios.json()} == {"geopolitical_shock", "macroeconomic_rate_shock", "credit_deterioration", "regulatory_shock", "broad_market_crash"}

    run = client.post("/stress-testing/run", json={"portfolio_id": portfolio.id, "scenario_id": "broad_market_crash", "risk_signal_id": signal.id, "trigger_mode": "automatic"})
    assert run.status_code == 200
    assert run.json()["reconciliation"]["reconciled"] is True

    history = client.get("/stress-testing/runs")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    detail = client.get(f"/stress-testing/runs/{run.json()['simulation_id']}")
    assert detail.status_code == 200
    assert detail.json()["input_snapshot"]["portfolio"]["id"] == portfolio.id

    low_signal = _seed_signal(db_session, event_type="market_crash", impact_score=7)
    rejected = client.post("/stress-testing/signals/{}/run".format(low_signal.id), json={})
    assert rejected.status_code == 422
    assert "below_impact_threshold" in rejected.json()["detail"]["reasons"]
