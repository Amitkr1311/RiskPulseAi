import json
from pathlib import Path

from sqlalchemy import select

from app.db.models import PortfolioPosition, StressScenario
from app.db.session import SessionLocal

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load_json(filename: str) -> list[dict[str, object]]:
    with (DATA_DIR / filename).open(encoding="utf-8") as data_file:
        return json.load(data_file)


def seed_database() -> None:
    with SessionLocal.begin() as db:
        if not db.scalar(select(PortfolioPosition.id).limit(1)):
            db.add_all(PortfolioPosition(**position) for position in _load_json("portfolio_seed.json"))
        if not db.scalar(select(StressScenario.id).limit(1)):
            db.add_all(StressScenario(**scenario) for scenario in _load_json("scenarios.json"))


if __name__ == "__main__":
    seed_database()
    print("RiskPulse foundation seed applied.")

