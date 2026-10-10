"""Add scoped synthetic portfolios and position metadata for Milestone 5."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_portfolio_foundation"
down_revision: Union[str, Sequence[str], None] = "0004_api_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_KEY = "demo-banking-portfolio"
LEGACY_KEYS = {
    "corporate_loan": "corporate_loans",
    "government_bond": "government_bonds",
    "corporate_bond": "corporate_bonds",
    "equity": "equities",
    "derivative": "derivatives",
}
LEGACY_PARAMETERS = {
    "corporate_loan": {
        "basis": "exposure",
        "borrower_group_id": "synthetic-borrower-group",
        "sector": "diversified",
        "pd": "0.025",
        "lgd": "0.60",
        "recovery_rate": "0.40",
        "remaining_tenor_years": "3.0",
    },
    "government_bond": {
        "basis": "market_value",
        "issuer": "Government of India",
        "maturity_year": 2032,
        "modified_duration": "6.0",
        "convexity": "42.0",
        "baseline_yield": "0.0715",
        "yield_unit": "decimal_rate",
    },
    "corporate_bond": {
        "basis": "market_value",
        "issuer": "Synthetic Investment Grade Issuer",
        "sector": "diversified",
        "credit_rating": "AA",
        "modified_duration": "4.0",
        "convexity": "22.0",
        "credit_spread_duration": "3.5",
        "baseline_credit_spread": "0.0180",
        "spread_unit": "decimal_rate",
    },
    "equity": {
        "basis": "market_value",
        "ticker": "SYNBANK",
        "instrument_name": "Synthetic Banking Equity Basket",
        "sector": "financials",
        "beta": "1.10",
        "market_reference": "synthetic broad market index",
    },
    "derivative": {
        "basis": "simplified_mark_to_market",
        "instrument_type": "index_total_return_swap",
        "underlying": "SYNBANK",
        "notional_exposure_inr": "100000000.00",
        "delta_equivalent": "0.50",
        "market_value_definition": "simplified_mark_to_market_portfolio_value",
    },
}


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_key"),
    )

    with op.batch_alter_table("portfolio_positions") as batch_op:
        batch_op.add_column(sa.Column("portfolio_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("position_key", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("is_demo", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))

    bind = op.get_bind()
    portfolios = sa.table(
        "portfolios",
        sa.column("id", sa.Integer),
        sa.column("portfolio_key", sa.String),
        sa.column("name", sa.String),
        sa.column("currency", sa.String),
        sa.column("is_demo", sa.Boolean),
        sa.column("description", sa.Text),
    )
    positions = sa.table(
        "portfolio_positions",
        sa.column("id", sa.Integer),
        sa.column("asset_type", sa.String),
        sa.column("portfolio_id", sa.Integer),
        sa.column("position_key", sa.String),
        sa.column("is_demo", sa.Boolean),
        sa.column("valuation_parameters", sa.JSON),
    )
    portfolio_id = bind.execute(
        sa.select(portfolios.c.id).where(portfolios.c.portfolio_key == DEMO_KEY)
    ).scalar_one_or_none()
    if portfolio_id is None:
        portfolio_id = bind.execute(
            portfolios.insert().values(
                portfolio_key=DEMO_KEY,
                name="Demo Banking Portfolio",
                currency="INR",
                is_demo=True,
                description="Deterministic synthetic portfolio for local development and testing.",
            ).returning(portfolios.c.id)
        ).scalar_one()

    legacy_rows = bind.execute(
        sa.select(positions.c.id, positions.c.asset_type)
        .where(positions.c.portfolio_id.is_(None))
        .order_by(positions.c.id)
    ).all()
    used_keys: set[str] = set()
    for position_id, asset_type in legacy_rows:
        base_key = LEGACY_KEYS.get(asset_type, f"legacy_{position_id}")
        position_key = base_key
        suffix = 1
        while position_key in used_keys:
            suffix += 1
            position_key = f"{base_key}_{suffix}"
        used_keys.add(position_key)
        values = {"portfolio_id": portfolio_id, "position_key": position_key, "is_demo": True}
        if asset_type in LEGACY_PARAMETERS:
            values["valuation_parameters"] = LEGACY_PARAMETERS[asset_type]
        bind.execute(positions.update().where(positions.c.id == position_id).values(**values))

    with op.batch_alter_table("portfolio_positions") as batch_op:
        batch_op.alter_column("portfolio_id", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("position_key", existing_type=sa.String(length=64), nullable=False)
        batch_op.alter_column("is_demo", existing_type=sa.Boolean(), nullable=False, server_default=sa.false())
        batch_op.alter_column("created_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.alter_column("updated_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.create_foreign_key(
            "fk_portfolio_positions_portfolio_id", "portfolios", ["portfolio_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_unique_constraint(
            "uq_portfolio_positions_portfolio_key", ["portfolio_id", "position_key"]
        )
        batch_op.create_index("ix_portfolio_positions_portfolio_id", ["portfolio_id"])
        batch_op.create_index("ix_portfolio_positions_asset_type", ["asset_type"])
        batch_op.create_index("ix_portfolio_positions_sector", ["sector"])


def downgrade() -> None:
    with op.batch_alter_table("portfolio_positions") as batch_op:
        batch_op.drop_index("ix_portfolio_positions_sector")
        batch_op.drop_index("ix_portfolio_positions_asset_type")
        batch_op.drop_index("ix_portfolio_positions_portfolio_id")
        batch_op.drop_constraint("uq_portfolio_positions_portfolio_key", type_="unique")
        batch_op.drop_constraint("fk_portfolio_positions_portfolio_id", type_="foreignkey")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("is_demo")
        batch_op.drop_column("position_key")
        batch_op.drop_column("portfolio_id")
    op.drop_table("portfolios")
