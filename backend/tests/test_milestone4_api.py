from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.db.models import Article, RiskSignal
from app.main import app


def _article(*, source: str, title: str, published_at: datetime | None, status: str, is_demo: bool) -> Article:
    return Article(
        source=source,
        title=title,
        text=f"Full article text for {title}",
        content_hash=f"m4-{title}",
        published_at=published_at,
        processing_status=status,
        is_demo=is_demo,
    )


def _signal(article: Article, *, event: str, impact: int, label: str, score: float, created_at: datetime) -> RiskSignal:
    return RiskSignal(
        article=article,
        entity_name="Tesla",
        sentiment_score=score,
        sentiment_label=label,
        sentiment_probabilities={"positive": 0.1, "negative": 0.7, "neutral": 0.2},
        event_type=event,
        event_confidence=0.9,
        impact_score=impact,
        impact_factors={"severity": 0.8},
        entities=[
            {
                "mention": "Tesla",
                "canonical_name": "Tesla",
                "identifier": None,
                "resolved": True,
                "entity_type": "organization",
            }
        ],
        explanation="Test explanation",
        model_version="test-v1",
        model_metadata={"backend": "test"},
        scoring_config_version="impact-v1",
        created_at=created_at,
    )


def seed_api_records(db_session) -> tuple[Article, Article, Article]:
    now = datetime.now(UTC)
    processed = _article(
        source="news",
        title="Tesla credit event",
        published_at=now - timedelta(days=2),
        status="processed",
        is_demo=True,
    )
    pending = _article(
        source="reddit",
        title="Macro discussion",
        published_at=now - timedelta(days=1),
        status="pending",
        is_demo=False,
    )
    failed = _article(source="news", title="Unpublished note", published_at=None, status="failed", is_demo=False)
    db_session.add_all([processed, pending, failed])
    db_session.flush()
    db_session.add(
        _signal(
            processed,
            event="credit_event",
            impact=8,
            label="negative",
            score=-0.6,
            created_at=now - timedelta(hours=2),
        )
    )
    db_session.add(
        _signal(
            pending,
            event="macroeconomic",
            impact=4,
            label="neutral",
            score=0,
            created_at=now - timedelta(hours=1),
        )
    )
    db_session.commit()
    return processed, pending, failed


def test_articles_support_filters_pagination_search_and_date_validation(client, db_session) -> None:
    processed, _pending, failed = seed_api_records(db_session)

    response = client.get("/articles?limit=1&offset=0&processing_status=processed&source=news")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == processed.id

    response = client.get("/articles?search=credit")
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = client.get("/articles?published_from=2030-01-01T00:00:00Z&published_to=2029-01-01T00:00:00Z")
    assert response.status_code == 422

    response = client.get(f"/articles/{failed.id}")
    assert response.status_code == 200
    assert response.json()["published_at"] is None


def test_signals_support_filters_latest_and_nested_article(client, db_session) -> None:
    processed, pending, _failed = seed_api_records(db_session)

    taxonomy = client.get("/signals/taxonomy")
    assert taxonomy.status_code == 200
    assert "credit_financial" in taxonomy.json()["event_groups"]
    assert "cyber_incident" in taxonomy.json()["event_types"]
    assert "central_bank" in taxonomy.json()["entity_types"]

    response = client.get("/signals?event_type=credit_event&impact_min=7&sentiment_label=negative&is_demo=true")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    signal = response.json()["items"][0]
    assert signal["article"]["id"] == processed.id
    assert signal["is_demo"] is True

    response = client.get("/signals?source=reddit&sentiment_min=-0.1&sentiment_max=0.1")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["article_id"] == pending.id

    response = client.get("/signals?event_group=credit_financial")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["event_group"] == "credit_financial"

    response = client.get("/signals?event_group=not-a-group")
    assert response.status_code == 422

    response = client.get("/signals/latest?limit=1")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["limit"] == 1

    response = client.get("/signals?impact_min=9&impact_max=2")
    assert response.status_code == 422


def test_dashboard_summary_uses_database_records(client, db_session) -> None:
    seed_api_records(db_session)
    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_articles"] == 3
    assert summary["processed_articles"] == 1
    assert summary["pending_articles"] == 1
    assert summary["failed_articles"] == 1
    assert summary["total_signals"] == 2
    assert summary["high_impact_signals"] == 1
    assert summary["demo_articles"] == 1
    assert summary["live_articles"] == 2


def test_database_errors_return_sanitized_503(client) -> None:
    def broken_db():
        raise SQLAlchemyError("internal database details")

    app.dependency_overrides[get_db] = broken_db
    response = client.get("/articles")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database service is unavailable"}
