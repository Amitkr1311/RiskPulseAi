"""Store historical replay status and source attribution on articles."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_article_history_metadata"
down_revision: Union[str, Sequence[str], None] = "0008_event_scenario_mapping"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "articles",
        sa.Column("is_historical", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("articles", sa.Column("source_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "source_metadata")
    op.drop_column("articles", "is_historical")
