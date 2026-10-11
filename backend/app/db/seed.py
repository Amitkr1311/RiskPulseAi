import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Portfolio, PortfolioPosition, StressScenario
from app.portfolio.scenarios import scenario_records
from app.schemas.portfolio import validate_position_parameters
from app.db.session import SessionLocal

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEMO_PORTFOLIO_KEY = "demo-banking-portfolio"


def _load_json(filename: str) -> list[dict[str, object]]:
    with (DATA_DIR / filename).open(encoding="utf-8") as data_file:
        return json.load(data_file)


def seed_demo_portfolio(db: Session) -> Portfolio:
    portfolio = db.scalar(select(Portfolio).where(Portfolio.portfolio_key == DEMO_PORTFOLIO_KEY))
    if portfolio is None:
        portfolio = Portfolio(
            portfolio_key=DEMO_PORTFOLIO_KEY,
            name="Demo Banking Portfolio",
            currency="INR",
            is_demo=True,
            description="Deterministic synthetic portfolio for local development and testing.",
        )
        db.add(portfolio)
        db.flush()
    seed_data = _load_json("portfolio_seed.json")
    legacy_derivative = db.scalar(
        select(PortfolioPosition).where(
            PortfolioPosition.portfolio_id == portfolio.id,
            PortfolioPosition.position_key == "derivatives",
            PortfolioPosition.is_demo.is_(True),
        )
    )
    if legacy_derivative is not None and not any(
        str(position["position_key"]) == "derivatives" for position in seed_data
    ):
        db.delete(legacy_derivative)
        db.flush()

    for position_data in seed_data:
        position_key = str(position_data["position_key"])
        existing = db.scalar(
            select(PortfolioPosition).where(
                PortfolioPosition.portfolio_id == portfolio.id,
                PortfolioPosition.position_key == position_key,
            )
        )
        if existing is not None:
            continue
        asset_type = str(position_data["asset_type"])
        parameters = validate_position_parameters(asset_type, position_data["valuation_parameters"])
        db.add(
            PortfolioPosition(
                portfolio_id=portfolio.id,
                position_key=position_key,
                name=position_data["name"],
                asset_type=asset_type,
                market_value=position_data["market_value"],
                currency=position_data.get("currency", "INR"),
                sector=position_data.get("sector"),
                borrower=position_data.get("borrower"),
                is_demo=True,
                valuation_parameters=parameters.model_dump(mode="json"),
            )
        )
    db.flush()
    return portfolio


def seed_database() -> None:
    with SessionLocal.begin() as db:
        seed_demo_portfolio(db)
        seed_scenarios(db)


def seed_scenarios(db: Session) -> list[StressScenario]:
    seeded: list[StressScenario] = []
    for scenario_data in scenario_records():
        scenario_key = str(scenario_data["scenario_key"])
        scenario = db.scalar(select(StressScenario).where(StressScenario.scenario_key == scenario_key))
        if scenario is None:
            scenario = db.scalar(select(StressScenario).where(StressScenario.name == scenario_data["name"]))
        if scenario is None:
            scenario = StressScenario(**scenario_data)
            db.add(scenario)
        else:
            for field, value in scenario_data.items():
                setattr(scenario, field, value)
        seeded.append(scenario)
    db.flush()
    return seeded


if __name__ == "__main__":
    seed_database()
    print("RiskPulse foundation seed applied.")
