"""Add indexes for Milestone 4 API filters and ordering."""

from typing import Sequence, Union

from alembic import op


revision: str = "0004_api_indexes"
down_revision: Union[str, Sequence[str], None] = "0003_nlp_signals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_articles_source", "articles", ["source"])
    op.create_index("ix_articles_published_at", "articles", ["published_at"])
    op.create_index("ix_articles_processing_status", "articles", ["processing_status"])
    op.create_index("ix_article_entities_entity_id", "article_entities", ["entity_id"])
    op.create_index("ix_risk_signals_event_type", "risk_signals", ["event_type"])
    op.create_index("ix_risk_signals_sentiment_label", "risk_signals", ["sentiment_label"])
    op.create_index("ix_risk_signals_impact_score", "risk_signals", ["impact_score"])
    op.create_index("ix_risk_signals_created_at", "risk_signals", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_risk_signals_created_at", table_name="risk_signals")
    op.drop_index("ix_risk_signals_impact_score", table_name="risk_signals")
    op.drop_index("ix_risk_signals_sentiment_label", table_name="risk_signals")
    op.drop_index("ix_risk_signals_event_type", table_name="risk_signals")
    op.drop_index("ix_article_entities_entity_id", table_name="article_entities")
    op.drop_index("ix_articles_processing_status", table_name="articles")
    op.drop_index("ix_articles_published_at", table_name="articles")
    op.drop_index("ix_articles_source", table_name="articles")
