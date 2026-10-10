from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.models import Article
from app.db.session import get_db
from app.services.api_queries import QueryRangeError, article_query, count_query, validate_range
from app.schemas.articles import ArticlePage, ArticleRead

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get(
    "",
    response_model=ArticlePage,
    summary="List ingested articles",
    description="Returns stable, paginated article records with source, processing, date, and optional text filters.",
)
def list_articles(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100_000),
    source: str | None = Query(default=None, min_length=1, max_length=32),
    processing_status: str | None = Query(default=None, min_length=1, max_length=32),
    published_from: datetime | None = Query(default=None),
    published_to: datetime | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=200),
    db: Session = Depends(get_db),
) -> ArticlePage:
    try:
        validate_range(published_from, published_to, "published")
    except QueryRangeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    query = article_query(
        source=source,
        processing_status=processing_status,
        published_from=published_from,
        published_to=published_to,
        search=search,
    )
    total = db.scalar(count_query(query)) or 0
    articles = db.scalars(
        query
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


@router.get(
    "/{article_id}",
    response_model=ArticleRead,
    summary="Get one ingested article",
    responses={404: {"description": "Article not found"}},
)
def get_article(article_id: int, db: Session = Depends(get_db)) -> ArticleRead:
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return ArticleRead.model_validate(article)
