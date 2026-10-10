from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.sql import Select

from app.db.models import Article, ArticleEntity, Entity, RiskSignal


class QueryRangeError(ValueError):
    pass


def validate_range(start: datetime | None, end: datetime | None, name: str) -> None:
    if start is not None and end is not None and _as_utc(start) > _as_utc(end):
        raise QueryRangeError(f"{name}_from must be less than or equal to {name}_to")


def as_utc(value: datetime | None) -> datetime | None:
    return _as_utc(value) if value is not None else None


def article_query(
    *,
    source: str | None = None,
    processing_status: str | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    search: str | None = None,
) -> Select[Any]:
    filters = []
    if source:
        filters.append(Article.source == source.strip().casefold())
    if processing_status:
        filters.append(Article.processing_status == processing_status.strip().casefold())
    if published_from:
        filters.append(Article.published_at >= _as_utc(published_from))
    if published_to:
        filters.append(Article.published_at <= _as_utc(published_to))
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(Article.title.ilike(pattern), Article.text.ilike(pattern)))
    return select(Article).where(*filters)


def signal_query(
    *,
    entity: str | None = None,
    event_type: str | None = None,
    impact_min: int | None = None,
    impact_max: int | None = None,
    sentiment_label: str | None = None,
    sentiment_min: float | None = None,
    sentiment_max: float | None = None,
    source: str | None = None,
    is_demo: bool | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> Select[Any]:
    filters = []
    if entity:
        pattern = f"%{entity.strip()}%"
        entity_match = (
            select(ArticleEntity.id)
            .join(Entity, Entity.id == ArticleEntity.entity_id)
            .where(ArticleEntity.article_id == RiskSignal.article_id)
            .where(Entity.canonical_name.ilike(pattern))
            .exists()
        )
        filters.append(or_(RiskSignal.entity_name.ilike(pattern), entity_match))
    if event_type:
        filters.append(RiskSignal.event_type == event_type.strip().casefold())
    if impact_min is not None:
        filters.append(RiskSignal.impact_score >= impact_min)
    if impact_max is not None:
        filters.append(RiskSignal.impact_score <= impact_max)
    if sentiment_label:
        filters.append(RiskSignal.sentiment_label == sentiment_label.strip().casefold())
    if sentiment_min is not None:
        filters.append(RiskSignal.sentiment_score >= sentiment_min)
    if sentiment_max is not None:
        filters.append(RiskSignal.sentiment_score <= sentiment_max)
    if source:
        filters.append(Article.source == source.strip().casefold())
    if is_demo is not None:
        filters.append(Article.is_demo == is_demo)
    if published_from:
        filters.append(Article.published_at >= _as_utc(published_from))
    if published_to:
        filters.append(Article.published_at <= _as_utc(published_to))
    if created_from:
        filters.append(RiskSignal.created_at >= _as_utc(created_from))
    if created_to:
        filters.append(RiskSignal.created_at <= _as_utc(created_to))
    return select(RiskSignal).join(Article).where(*filters)


def count_query(query: Select[Any]):
    return select(func.count()).select_from(query.order_by(None).subquery())


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
