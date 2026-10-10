from datetime import UTC, datetime
from decimal import Decimal

from app.db.models import Article


def _article(source: str, external_id: str, title: str, published_at: datetime):
    return Article(
        source=source,
        external_id=external_id,
        title=title,
        text=f"Text for {title}",
        url=f"https://example.test/{external_id}",
        published_at=published_at,
        ingested_at=published_at,
        content_hash=external_id * 4,
        is_demo=True,
    )


def test_articles_endpoint_supports_pagination_and_source_filter(client, db_session):
    db_session.add_all(
        [
            _article("news", "a1", "News one", datetime(2026, 1, 1, tzinfo=UTC)),
            _article("reddit", "a2", "Reddit one", datetime(2026, 1, 2, tzinfo=UTC)),
            _article("news", "a3", "News two", datetime(2026, 1, 3, tzinfo=UTC)),
        ]
    )
    db_session.commit()

    response = client.get("/articles", params={"source": "news", "limit": 1, "offset": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["limit"] == 1
    assert payload["offset"] == 1
    assert payload["items"][0]["external_id"] == "a1"


def test_articles_endpoint_validates_pagination_and_missing_records(client):
    assert client.get("/articles", params={"limit": 0}).status_code == 422
    assert client.get("/articles", params={"limit": 101}).status_code == 422
    assert client.get("/articles/999").status_code == 404


def test_demo_endpoint_loads_fixtures_and_is_idempotent(client):
    first = client.post("/ingestion/demo")
    second = client.post("/ingestion/demo")

    assert first.status_code == 200
    assert first.json()["inserted"] == 4
    assert second.status_code == 200
    assert second.json()["duplicates_skipped"] == 4


def test_live_ingestion_without_credentials_is_gracefully_disabled(client):
    response = client.post("/ingestion/run", json={"sources": ["news", "reddit"], "limit": 5})

    assert response.status_code == 200
    assert {run["status"] for run in response.json()["runs"]} == {"disabled"}
    assert {run["error_category"] for run in response.json()["runs"]} == {"not_configured"}


def test_ingestion_status_exposes_source_configuration_and_recent_runs(client):
    client.post("/ingestion/demo")

    response = client.get("/ingestion/status")

    assert response.status_code == 200
    assert {source["source"] for source in response.json()["sources"]} == {"news", "reddit"}
    assert response.json()["recent_runs"][0]["source"] == "demo"

