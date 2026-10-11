from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_articles_source_external_id"),
        UniqueConstraint("source", "content_hash", name="uq_articles_source_content_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    is_historical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    source_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    processing_error: Mapped[str | None] = mapped_column(String(128))
    processing_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    entities: Mapped[list["ArticleEntity"]] = relationship(back_populates="article", cascade="all, delete-orphan")
    signals: Mapped[list["RiskSignal"]] = relationship(back_populates="article", cascade="all, delete-orphan")


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    identifier: Mapped[str | None] = mapped_column(String(64))
    aliases: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, default="organization")

    articles: Mapped[list["ArticleEntity"]] = relationship(back_populates="entity")
    signals: Mapped[list["RiskSignal"]] = relationship(back_populates="entity")


class ArticleEntity(Base):
    __tablename__ = "article_entities"
    __table_args__ = (UniqueConstraint("article_id", "entity_id", name="uq_article_entities_article_entity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_mention: Mapped[str] = mapped_column(String(255), nullable=False)
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))

    article: Mapped[Article] = relationship(back_populates="entities")
    entity: Mapped[Entity] = relationship(back_populates="articles")


class RiskSignal(Base):
    __tablename__ = "risk_signals"
    __table_args__ = (UniqueConstraint("article_id", name="uq_risk_signals_article_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    entity_name: Mapped[str | None] = mapped_column(String(255))
    sentiment_score: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    sentiment_label: Mapped[str | None] = mapped_column(String(16), index=True)
    sentiment_probabilities: Mapped[dict[str, object] | None] = mapped_column(JSON)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    impact_score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    impact_factors: Mapped[dict[str, object] | None] = mapped_column(JSON)
    entities: Mapped[list[dict[str, object]] | None] = mapped_column(JSON)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    model_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON)
    scoring_config_version: Mapped[str] = mapped_column(String(64), nullable=False, default="impact-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    article: Mapped[Article] = relationship(back_populates="signals")
    entity: Mapped[Entity | None] = relationship(back_populates="signals")
    stress_runs: Mapped[list["StressTestRun"]] = relationship(
        back_populates="trigger_signal",
        foreign_keys="StressTestRun.trigger_signal_id",
    )
    triggered_stress_runs: Mapped[list["StressTestRun"]] = relationship(
        back_populates="triggered_by_signal",
        foreign_keys="StressTestRun.triggered_by_signal_id",
    )


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    positions: Mapped[list["PortfolioPosition"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    stress_runs: Mapped[list["StressTestRun"]] = relationship(back_populates="portfolio")


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"
    __table_args__ = (UniqueConstraint("portfolio_id", "position_key", name="uq_portfolio_positions_portfolio_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    sector: Mapped[str | None] = mapped_column(String(128), index=True)
    borrower: Mapped[str | None] = mapped_column(String(255))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    valuation_parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    portfolio: Mapped[Portfolio] = relationship(back_populates="positions")
    results: Mapped[list["StressTestResult"]] = relationship(back_populates="position")


class StressScenario(Base):
    __tablename__ = "stress_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    event_category: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    shock_parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    assumptions: Mapped[str] = mapped_column(Text, nullable=False)

    runs: Mapped[list["StressTestRun"]] = relationship(back_populates="scenario")


class StressTestRun(Base):
    __tablename__ = "stress_test_runs"
    __table_args__ = (UniqueConstraint("trigger_key", name="uq_stress_test_runs_trigger_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    trigger_key: Mapped[str] = mapped_column(String(255), nullable=False)
    portfolio_id: Mapped[int | None] = mapped_column(ForeignKey("portfolios.id", ondelete="SET NULL"), index=True)
    trigger_signal_id: Mapped[int | None] = mapped_column(ForeignKey("risk_signals.id", ondelete="SET NULL"))
    triggered_by_signal_id: Mapped[int | None] = mapped_column(
        ForeignKey("risk_signals.id", ondelete="SET NULL"), index=True
    )
    scenario_id: Mapped[int] = mapped_column(ForeignKey("stress_scenarios.id"), nullable=False)
    portfolio_value_before: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    portfolio_value_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    loss_percentage: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    portfolio_return_percentage: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    trigger_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    scenario_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="stress-v1")
    scenario_parameters: Mapped[dict[str, object] | None] = mapped_column(JSON)
    input_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON)
    data_provenance: Mapped[dict[str, object] | None] = mapped_column(JSON)
    validation_warnings: Mapped[list[str] | None] = mapped_column(JSON)
    reconciliation_tolerance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.01"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    portfolio: Mapped[Portfolio | None] = relationship(back_populates="stress_runs")
    trigger_signal: Mapped[RiskSignal | None] = relationship(
        back_populates="stress_runs",
        foreign_keys=[trigger_signal_id],
    )
    triggered_by_signal: Mapped[RiskSignal | None] = relationship(
        back_populates="triggered_stress_runs",
        foreign_keys=[triggered_by_signal_id],
    )
    scenario: Mapped[StressScenario] = relationship(back_populates="runs")
    results: Mapped[list["StressTestResult"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class StressTestResult(Base):
    __tablename__ = "stress_test_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("stress_test_runs.id", ondelete="CASCADE"), nullable=False)
    position_id: Mapped[int] = mapped_column(ForeignKey("portfolio_positions.id"), nullable=False)
    position_value_before: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    position_value_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    contribution: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    position_key_snapshot: Mapped[str | None] = mapped_column(String(64))
    position_name_snapshot: Mapped[str | None] = mapped_column(String(255))
    asset_type_snapshot: Mapped[str | None] = mapped_column(String(64))
    inclusion_status: Mapped[str] = mapped_column(String(32), nullable=False, default="included")
    calculation_method: Mapped[str | None] = mapped_column(String(128))
    explanation: Mapped[str | None] = mapped_column(Text)
    calculation_details: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)

    run: Mapped[StressTestRun] = relationship(back_populates="results")
    position: Mapped[PortfolioPosition] = relationship(back_populates="results")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    records_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_category: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SocialReplayState(Base):
    __tablename__ = "social_replay_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="idle", index=True)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    speed_records_per_second: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False, default=1)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_record_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
