"""Persist the historical social replay cursor and counters."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_social_replay_state"
down_revision: Union[str, Sequence[str], None] = "0009_article_history_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "social_replay_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset_path", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="idle"),
        sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_attempted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicates_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("speed_records_per_second", sa.Numeric(8, 3), nullable=False, server_default="1"),
        sa.Column("batch_size", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_record_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("social_replay_state")
