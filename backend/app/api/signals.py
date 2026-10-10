from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import Article, ArticleEntity, RiskSignal
from app.nlp.entities import ENTITY_TYPES
from app.nlp.events import EVENT_GROUPS, EVENT_TYPES, event_group_for_type
from app.db.session import get_db
from app.schemas.articles import ArticleRead
from app.schemas.signals import EntitySignalRead, RiskSignalRead, SignalPage, SignalTaxonomy
from app.services.api_queries import QueryRangeError, count_query, signal_query, validate_range

router = APIRouter(prefix="/signals", tags=["signals"])
SIGNAL_OPTIONS = joinedload(RiskSignal.article).selectinload(Article.entities).joinedload(ArticleEntity.entity)
SENTIMENT_LABELS = {"positive", "negative", "neutral"}


def _as_read(signal: RiskSignal) -> RiskSignalRead:
    raw_entities = signal.entities
    if raw_entities is None:
        raw_entities = [
            {
                "mention": relation.raw_mention,
                "canonical_name": relation.entity.canonical_name,
                "identifier": relation.entity.identifier,
                "resolved": relation.entity.identifier is not None,
                "entity_type": relation.entity.entity_type,
            }
            for relation in signal.article.entities
        ]
    entities = [EntitySignalRead.model_validate(entity) for entity in raw_entities]
    article = ArticleRead.model_validate(signal.article)
    return RiskSignalRead(
        id=signal.id,
        article_id=signal.article_id,
        source=signal.article.source,
        article_title=signal.article.title,
        article_url=signal.article.url,
        is_demo=signal.article.is_demo,
        article=article,
        entities=entities,
        sentiment_label=signal.sentiment_label,
        sentiment_score=float(signal.sentiment_score),
        sentiment_probabilities=(
            {key: float(value) for key, value in signal.sentiment_probabilities.items()}
            if signal.sentiment_probabilities is not None
            else None
        ),
        event_type=signal.event_type,
        event_group=event_group_for_type(signal.event_type),
        event_confidence=float(signal.event_confidence) if signal.event_confidence is not None else None,
        impact_score=signal.impact_score,
        impact_factors=signal.impact_factors,
        explanation=signal.explanation,
        model_version=signal.model_version,
        model_metadata=signal.model_metadata,
        scoring_config_version=signal.scoring_config_version,
        created_at=signal.created_at,
    )


@router.get(
    "",
    response_model=SignalPage,
    summary="List persisted risk signals",
    description="Returns paginated NLP signals with optional source, entity, event, sentiment, impact, demo, and date filters.",
)
def list_signals(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100_000),
    event_type: str | None = Query(default=None, min_length=1, max_length=64),
    event_group: str | None = Query(default=None, min_length=1, max_length=64),
    source: str | None = Query(default=None, min_length=1, max_length=32),
    entity: str | None = Query(default=None, min_length=1, max_length=255),
    sentiment_label: str | None = Query(default=None, min_length=1, max_length=16),
    sentiment_min: float | None = Query(default=None, ge=-1, le=1),
    sentiment_max: float | None = Query(default=None, ge=-1, le=1),
    impact_min: int | None = Query(default=None, ge=1, le=10),
    impact_max: int | None = Query(default=None, ge=1, le=10),
    is_demo: bool | None = Query(default=None),
    published_from: datetime | None = Query(default=None),
    published_to: datetime | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SignalPage:
    _validate_signal_filters(
        event_type,
        event_group,
        sentiment_label,
        sentiment_min,
        sentiment_max,
        impact_min,
        impact_max,
        published_from,
        published_to,
        created_from,
        created_to,
    )
    return _signal_page(
        db,
        limit=limit,
        offset=offset,
        entity=entity,
        event_type=event_type,
        event_group=event_group,
        impact_min=impact_min,
        impact_max=impact_max,
        sentiment_label=sentiment_label,
        sentiment_min=sentiment_min,
        sentiment_max=sentiment_max,
        source=source,
        is_demo=is_demo,
        published_from=published_from,
        published_to=published_to,
        created_from=created_from,
        created_to=created_to,
    )


@router.get(
    "/taxonomy",
    response_model=SignalTaxonomy,
    summary="Get supported signal taxonomy",
    description="Returns the broad event groups, detailed event types, and entity types used by the NLP pipeline.",
)
def signal_taxonomy() -> SignalTaxonomy:
    return SignalTaxonomy(
        event_groups={key: list(values) for key, values in EVENT_GROUPS.items()},
        event_types=list(EVENT_TYPES),
        entity_types=list(ENTITY_TYPES),
    )


@router.get(
    "/latest",
    response_model=SignalPage,
    summary="Get the latest risk signals",
    description="Returns the most recently created signals, newest first, with a maximum of 50 records.",
)
def latest_signals(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> SignalPage:
    return _signal_page(db, limit=limit, offset=0)


@router.get(
    "/{signal_id}",
    response_model=RiskSignalRead,
    summary="Get one risk signal with its source article",
    responses={404: {"description": "Risk signal not found"}},
)
def get_signal(signal_id: int, db: Session = Depends(get_db)) -> RiskSignalRead:
    signal = db.scalar(select(RiskSignal).options(SIGNAL_OPTIONS).where(RiskSignal.id == signal_id))
    if signal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk signal not found")
    return _as_read(signal)


def _signal_page(db: Session, *, limit: int, offset: int, **filters: Any) -> SignalPage:
    query = signal_query(**filters)
    total = db.scalar(count_query(query)) or 0
    signals = db.scalars(
        query.options(SIGNAL_OPTIONS)
        .order_by(RiskSignal.created_at.desc(), RiskSignal.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return SignalPage(items=[_as_read(signal) for signal in signals], total=total, limit=limit, offset=offset)


def _validate_signal_filters(
    event_type: str | None,
    event_group: str | None,
    sentiment_label: str | None,
    sentiment_min: float | None,
    sentiment_max: float | None,
    impact_min: int | None,
    impact_max: int | None,
    published_from: datetime | None,
    published_to: datetime | None,
    created_from: datetime | None,
    created_to: datetime | None,
) -> None:
    if event_type is not None and not event_type.strip():
        raise HTTPException(status_code=422, detail="event_type must not be blank")
    if event_group is not None and event_group.strip().casefold() not in EVENT_GROUPS:
        raise HTTPException(status_code=422, detail="event_group is not supported")
    if sentiment_label is not None and sentiment_label.strip().casefold() not in SENTIMENT_LABELS:
        raise HTTPException(status_code=422, detail="sentiment_label must be positive, negative, or neutral")
    if sentiment_min is not None and sentiment_max is not None and sentiment_min > sentiment_max:
        raise HTTPException(status_code=422, detail="sentiment_min must be less than or equal to sentiment_max")
    if impact_min is not None and impact_max is not None and impact_min > impact_max:
        raise HTTPException(status_code=422, detail="impact_min must be less than or equal to impact_max")
    try:
        validate_range(published_from, published_to, "published")
        validate_range(created_from, created_to, "created")
    except QueryRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
