from collections.abc import Mapping
from decimal import Decimal

from sqlalchemy import func, select

from app.core.config import Settings
from app.db.models import Article, IngestionRun
from app.ingestion.adapters.demo import DemoAdapter
from app.ingestion.errors import ProviderTransientError, ProviderTimeoutError
from app.ingestion.normalization import NormalizedArticle
from app.ingestion.service import IngestionService


class FakeAdapter:
    source_name = "fake"

    def __init__(self, records: list[Mapping[str, object]], failures: int = 0, error=None):
        self.records = records
        self.failures = failures
        self.error = error or ProviderTimeoutError("temporary failure")
        self.fetch_calls = 0

    @property
    def configured(self):
        return True

    def fetch(self, limit: int, offset: int = 0):
        self.fetch_calls += 1
        if self.fetch_calls <= self.failures:
            raise self.error
        return self.records[offset : offset + limit]

    def normalize(self, record):
        return NormalizedArticle(**record)


def _settings(**overrides):
    values = {
        "ingestion_max_retries": 2,
        "ingestion_retry_backoff_seconds": 0,
    }
    values.update(overrides)
    return Settings(**values)


def _record(external_id=None, title="Title", text="Body"):
    return {
        "source": "news",
        "external_id": external_id,
        "title": title,
        "text": text,
        "url": "https://example.test/article",
        "published_at": "2026-01-19T10:00:00Z",
        "is_demo": False,
    }


def test_repeated_provider_id_is_skipped(db_session):
    adapter = FakeAdapter([_record("same-id")])
    service = IngestionService(db_session, {"fake": adapter}, _settings())

    first, second = service.run(["fake", "fake"], limit=10)

    assert first.inserted == 1
    assert second.inserted == 0
    assert second.duplicates_skipped == 1
    assert db_session.scalar(select(func.count(Article.id))) == 1


def test_missing_provider_id_uses_content_hash_for_deduplication(db_session):
    adapter = FakeAdapter([_record(None, "Same title", "Same body")])
    service = IngestionService(db_session, {"fake": adapter}, _settings())

    first, second = service.run(["fake", "fake"], limit=10)

    assert first.inserted == 1
    assert second.duplicates_skipped == 1
    assert db_session.scalar(select(func.count(Article.id))) == 1


def test_transient_provider_failure_is_retried_with_bounded_backoff(db_session):
    adapter = FakeAdapter([_record("retry-id")], failures=2)
    delays: list[float] = []
    service = IngestionService(db_session, {"fake": adapter}, _settings(), sleep=delays.append)

    result = service.run(["fake"])[0]

    assert result.status == "completed"
    assert result.inserted == 1
    assert adapter.fetch_calls == 3
    assert delays == [0, 0]


def test_one_source_failure_does_not_stop_another_source(db_session):
    failing = FakeAdapter([], failures=3, error=ProviderTransientError("provider unavailable"))
    working = FakeAdapter([_record("working-id")])
    service = IngestionService(
        db_session,
        {"failed": failing, "working": working},
        _settings(ingestion_max_retries=0),
    )

    failed_result, working_result = service.run(["failed", "working"])

    assert failed_result.status == "failed"
    assert failed_result.error_category == "transient"
    assert working_result.status == "completed"
    assert working_result.inserted == 1


def test_demo_fixtures_are_repeatable_and_marked_as_demo(db_session):
    service = IngestionService(db_session, {"demo": DemoAdapter()}, _settings())

    first, second = service.run(["demo", "demo"], limit=100)

    assert first.inserted == 4
    assert second.duplicates_skipped == 4
    articles = db_session.scalars(select(Article).order_by(Article.id)).all()
    assert len(articles) == 4
    assert all(article.is_demo for article in articles)
    assert {article.source for article in articles} == {"news", "reddit"}
    assert db_session.scalar(select(func.count(IngestionRun.id))) == 2
