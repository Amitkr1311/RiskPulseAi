from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Article
from app.db.session import get_db
from app.schemas.articles import ArticlePage, ArticleRead

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=ArticlePage)
def list_articles(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100_000),
    source: str | None = Query(default=None, min_length=1, max_length=32),
    published_from: datetime | None = Query(default=None),
    published_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ArticlePage:
    filters = []
    if source:
        filters.append(Article.source == source.strip().lower())
    if published_from:
        filters.append(Article.published_at >= _as_utc(published_from))
    if published_to:
        filters.append(Article.published_at <= _as_utc(published_to))

    total = db.scalar(select(func.count()).select_from(Article).where(*filters)) or 0
    articles = db.scalars(
        select(Article)
        .where(*filters)
        .order_by(Article.published_at.desc().nullslast(), Article.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return ArticlePage(
        items=[ArticleRead.model_validate(article) for article in articles],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(article_id: int, db: Session = Depends(get_db)) -> ArticleRead:
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return ArticleRead.model_validate(article)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

