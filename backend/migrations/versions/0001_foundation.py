"""Create the RiskPulse foundation schema.

Revision ID: 0001_foundation
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_foundation"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("processing_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_articles_source_external_id"),
    )
    op.create_index("ix_articles_content_hash", "articles", ["content_hash"])
    op.create_table(
        "entities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("identifier", sa.String(length=64), nullable=True),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False, server_default="organization"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_name"),
    )
    op.create_table(
        "article_entities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("raw_mention", sa.String(length=255), nullable=False),
        sa.Column("extraction_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id", "entity_id", name="uq_article_entities_article_entity"),
    )
    op.create_table(
        "risk_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("entity_name", sa.String(length=255), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("impact_score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "portfolio_positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("market_value", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("sector", sa.String(length=128), nullable=True),
        sa.Column("borrower", sa.String(length=255), nullable=True),
        sa.Column("valuation_parameters", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "stress_scenarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("event_category", sa.String(length=64), nullable=False),
        sa.Column("trigger_threshold", sa.Integer(), nullable=False),
        sa.Column("shock_parameters", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("assumptions", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "stress_test_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trigger_key", sa.String(length=255), nullable=False),
        sa.Column("trigger_signal_id", sa.Integer(), nullable=True),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("portfolio_value_before", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("portfolio_value_after", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("pnl", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("loss_percentage", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["stress_scenarios.id"]),
        sa.ForeignKeyConstraint(["trigger_signal_id"], ["risk_signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trigger_key", name="uq_stress_test_runs_trigger_key"),
    )
    op.create_table(
        "stress_test_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=False),
        sa.Column("position_value_before", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("position_value_after", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("contribution", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("calculation_details", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["position_id"], ["portfolio_positions.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["stress_test_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("records_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_runs")
    op.drop_table("stress_test_results")
    op.drop_table("stress_test_runs")
    op.drop_table("stress_scenarios")
    op.drop_table("portfolio_positions")
    op.drop_table("risk_signals")
    op.drop_table("article_entities")
    op.drop_table("entities")
    op.drop_index("ix_articles_content_hash", table_name="articles")
    op.drop_table("articles")

