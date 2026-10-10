from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Article, ArticleEntity, Entity, RiskSignal
from app.db.session import get_db
from app.schemas.signals import EntitySignalRead, RiskSignalRead, SignalPage

router = APIRouter(prefix="/signals", tags=["signals"])


def _as_read(signal: RiskSignal) -> RiskSignalRead:
    raw_entities = signal.entities or []
    entities = [EntitySignalRead.model_validate(entity) for entity in raw_entities]
    probabilities = signal.sentiment_probabilities or {"positive": 0.0, "negative": 0.0, "neutral": 1.0}
    metadata = signal.model_metadata or {}
    return RiskSignalRead(
        id=signal.id,
        article_id=signal.article_id,
        source=signal.article.source,
        article_title=signal.article.title,
        article_url=signal.article.url,
        entities=entities,
        sentiment_label=signal.sentiment_label or "neutral",
        sentiment_score=float(signal.sentiment_score),
        sentiment_probabilities={key: float(value) for key, value in probabilities.items()},
        event_type=signal.event_type,
        event_confidence=float(signal.event_confidence) if signal.event_confidence is not None else None,
        impact_score=signal.impact_score,
        impact_factors=signal.impact_factors or {},
        explanation=signal.explanation,
        model_version=signal.model_version,
        model_metadata=metadata,
        scoring_config_version=signal.scoring_config_version,
        created_at=signal.created_at,
    )


@router.get("", response_model=SignalPage)
def list_signals(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100_000),
    event_type: str | None = Query(default=None, min_length=1, max_length=64),
    source: str | None = Query(default=None, min_length=1, max_length=32),
    entity: str | None = Query(default=None, min_length=1, max_length=255),
    impact_min: int | None = Query(default=None, ge=1, le=10),
    impact_max: int | None = Query(default=None, ge=1, le=10),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SignalPage:
    filters: list[Any] = []
    if event_type:
        filters.append(RiskSignal.event_type == event_type.strip().casefold())
    if source:
        filters.append(Article.source == source.strip().casefold())
    if impact_min is not None:
        filters.append(RiskSignal.impact_score >= impact_min)
    if impact_max is not None:
        filters.append(RiskSignal.impact_score <= impact_max)
    if created_from:
        filters.append(RiskSignal.created_at >= _as_utc(created_from))
    if created_to:
        filters.append(RiskSignal.created_at <= _as_utc(created_to))
    query = select(RiskSignal).join(Article)
    if entity:
        entity_pattern = f"%{entity.strip()}%"
        entity_match = (
            select(ArticleEntity.id)
            .join(Entity, Entity.id == ArticleEntity.entity_id)
            .where(ArticleEntity.article_id == RiskSignal.article_id)
            .where(Entity.canonical_name.ilike(entity_pattern))
            .exists()
        )
        filters.append(or_(RiskSignal.entity_name.ilike(entity_pattern), entity_match))
    query = query.where(*filters)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    signals = db.scalars(query.order_by(RiskSignal.created_at.desc(), RiskSignal.id.desc()).offset(offset).limit(limit)).all()
    return SignalPage(items=[_as_read(signal) for signal in signals], total=total, limit=limit, offset=offset)


@router.get("/{signal_id}", response_model=RiskSignalRead)
def get_signal(signal_id: int, db: Session = Depends(get_db)) -> RiskSignalRead:
    signal = db.get(RiskSignal, signal_id)
    if signal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk signal not found")
    return _as_read(signal)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
