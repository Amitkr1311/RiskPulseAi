"""Prepare article and ingestion tables for Milestone 2.

Revision ID: 0002_ingestion_foundation
Revises: 0001_foundation
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_ingestion_foundation"
down_revision: Union[str, Sequence[str], None] = "0001_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("articles") as batch_op:
        batch_op.alter_column("external_id", existing_type=sa.String(length=255), nullable=True)
        batch_op.alter_column("is_demo", existing_type=sa.Boolean(), server_default=sa.false())
        batch_op.create_unique_constraint("uq_articles_source_content_hash", ["source", "content_hash"])

    with op.batch_alter_table("ingestion_runs") as batch_op:
        batch_op.add_column(sa.Column("duplicates_skipped", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("error_category", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("ingestion_runs") as batch_op:
        batch_op.drop_column("error_category")
        batch_op.drop_column("records_failed")
        batch_op.drop_column("duplicates_skipped")

    with op.batch_alter_table("articles") as batch_op:
        batch_op.drop_constraint("uq_articles_source_content_hash", type_="unique")
        batch_op.alter_column("is_demo", existing_type=sa.Boolean(), server_default=sa.true())
        batch_op.alter_column("external_id", existing_type=sa.String(length=255), nullable=False)

