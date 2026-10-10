"""Add Milestone 3 NLP processing and signal metadata."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_nlp_signals"
down_revision: Union[str, Sequence[str], None] = "0002_ingestion_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("articles") as batch_op:
        batch_op.add_column(sa.Column("processing_error", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("processing_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("risk_signals") as batch_op:
        batch_op.alter_column("entity_name", existing_type=sa.String(length=255), nullable=True)
        batch_op.add_column(sa.Column("sentiment_label", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("sentiment_probabilities", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("event_confidence", sa.Numeric(6, 4), nullable=True))
        batch_op.add_column(sa.Column("impact_factors", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("entities", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("model_metadata", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("scoring_config_version", sa.String(length=64), nullable=False, server_default="impact-v1")
        )
        batch_op.create_unique_constraint("uq_risk_signals_article_id", ["article_id"])


def downgrade() -> None:
    with op.batch_alter_table("risk_signals") as batch_op:
        batch_op.drop_constraint("uq_risk_signals_article_id", type_="unique")
        batch_op.drop_column("scoring_config_version")
        batch_op.drop_column("model_metadata")
        batch_op.drop_column("entities")
        batch_op.drop_column("impact_factors")
        batch_op.drop_column("event_confidence")
        batch_op.drop_column("sentiment_probabilities")
        batch_op.drop_column("sentiment_label")
        batch_op.alter_column("entity_name", existing_type=sa.String(length=255), nullable=False)

    with op.batch_alter_table("articles") as batch_op:
        batch_op.drop_column("processed_at")
        batch_op.drop_column("processing_attempts")
        batch_op.drop_column("processing_error")
