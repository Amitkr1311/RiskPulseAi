"""Add named corporate demo exposures for signal-to-portfolio matching."""

import json
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_named_corporate_exposures"
down_revision: Union[str, Sequence[str], None] = "0010_social_replay_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_KEY = "demo-banking-portfolio"


def _seed_records() -> list[dict[str, object]]:
    data_path = Path(__file__).resolve().parents[2] / "data" / "portfolio_seed.json"
    with data_path.open(encoding="utf-8") as data_file:
        return json.load(data_file)


def upgrade() -> None:
    bind = op.get_bind()
    portfolios = sa.table(
        "portfolios",
        sa.column("id", sa.Integer),
        sa.column("portfolio_key", sa.String),
    )
    positions = sa.table(
        "portfolio_positions",
        sa.column("id", sa.Integer),
        sa.column("portfolio_id", sa.Integer),
        sa.column("position_key", sa.String),
        sa.column("name", sa.String),
        sa.column("asset_type", sa.String),
        sa.column("market_value", sa.Numeric),
        sa.column("currency", sa.String),
        sa.column("sector", sa.String),
        sa.column("borrower", sa.String),
        sa.column("is_demo", sa.Boolean),
        sa.column("valuation_parameters", sa.JSON),
    )
    portfolio_id = bind.execute(
        sa.select(portfolios.c.id).where(portfolios.c.portfolio_key == DEMO_KEY)
    ).scalar_one_or_none()
    if portfolio_id is None:
        return

    records = _seed_records()
    for record in records:
        position_key = str(record["position_key"])
        existing = bind.execute(
            sa.select(positions.c.id, positions.c.is_demo)
            .where(positions.c.portfolio_id == portfolio_id)
            .where(positions.c.position_key == position_key)
        ).first()
        values = {
            "name": record["name"],
            "asset_type": record["asset_type"],
            "market_value": record["market_value"],
            "currency": record.get("currency", "INR"),
            "sector": record.get("sector"),
            "borrower": record.get("borrower"),
            "is_demo": True,
            "valuation_parameters": record["valuation_parameters"],
        }
        if existing is not None:
            if existing.is_demo:
                bind.execute(
                    positions.update()
                    .where(positions.c.id == existing.id)
                    .values(**values)
                )
            continue
        bind.execute(
            positions.insert().values(
                portfolio_id=portfolio_id,
                position_key=position_key,
                **values,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    positions = sa.table(
        "portfolio_positions",
        sa.column("portfolio_id", sa.Integer),
        sa.column("position_key", sa.String),
        sa.column("is_demo", sa.Boolean),
        sa.column("market_value", sa.Numeric),
    )
    portfolios = sa.table(
        "portfolios",
        sa.column("id", sa.Integer),
        sa.column("portfolio_key", sa.String),
    )
    portfolio_id = bind.execute(
        sa.select(portfolios.c.id).where(portfolios.c.portfolio_key == DEMO_KEY)
    ).scalar_one_or_none()
    if portfolio_id is None:
        return
    named_keys = [
        "tesla_corporate_loan", "apple_corporate_loan", "microsoft_corporate_loan", "hdfc_bank_corporate_loan",
        "tesla_corporate_bond", "apple_corporate_bond", "microsoft_corporate_bond", "hdfc_bank_corporate_bond",
        "tesla_equity", "apple_equity", "microsoft_equity", "hdfc_bank_equity",
    ]
    bind.execute(
        positions.delete()
        .where(positions.c.portfolio_id == portfolio_id)
        .where(positions.c.position_key.in_(named_keys))
        .where(positions.c.is_demo.is_(True))
    )
    bind.execute(
        positions.update()
        .where(positions.c.portfolio_id == portfolio_id)
        .where(positions.c.position_key == "corporate_loans")
        .values(market_value="400000000.00")
    )
    bind.execute(
        positions.update()
        .where(positions.c.portfolio_id == portfolio_id)
        .where(positions.c.position_key == "corporate_bonds")
        .values(market_value="200000000.00")
    )
    bind.execute(
        positions.update()
        .where(positions.c.portfolio_id == portfolio_id)
        .where(positions.c.position_key == "equities")
        .values(market_value="100000000.00")
    )
