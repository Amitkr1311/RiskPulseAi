from datetime import UTC, datetime

from app.core.config import Settings
from app.db.models import Article, RiskSignal
from app.nlp.service import NLPService


def _article(title: str, text: str, source: str = "news") -> Article:
    return Article(
        source=source,
        external_id=None,
        title=title,
        text=text,
        url=None,
        published_at=datetime.now(UTC),
        content_hash=f"hash-{title}",
        is_demo=True,
        processing_status="pending",
    )


def test_pipeline_persists_signal_entities_and_is_idempotent(db_session) -> None:
    article = _article("Tesla earnings", "Tesla reported strong profit growth after quarterly earnings.")
    db_session.add(article)
    db_session.commit()
    service = NLPService(db_session, Settings())

    first = service.process_article(article.id)
    second = service.process_article(article.id)
    signal = db_session.get(RiskSignal, first.signal_id)

    assert first.status == "processed"
    assert second.status == "skipped"
    assert signal is not None
    assert signal.event_type == "earnings"
    assert signal.sentiment_label == "positive"
    assert signal.entities[0]["canonical_name"] == "Tesla"
    assert db_session.query(RiskSignal).count() == 1
    assert db_session.get(Article, article.id).processing_status == "processed"


def test_pipeline_marks_bad_text_failed_without_signal(db_session) -> None:
    article = _article("", "")
    db_session.add(article)
    db_session.commit()
    result = NLPService(db_session, Settings()).process_article(article.id)
    stored = db_session.get(Article, article.id)
    assert result.status == "failed"
    assert stored.processing_status == "failed"
    assert stored.processing_error == "empty_text"
    assert db_session.query(RiskSignal).count() == 0


def test_pipeline_batch_only_processes_requested_records(db_session) -> None:
    db_session.add_all(
        [
            _article("One", "Revenue growth was strong"),
            _article("Two", "The central bank changed interest rates"),
            _article("Three", "A merger was announced"),
        ]
    )
    db_session.commit()
    result = NLPService(db_session, Settings()).process_pending(limit=2)
    assert result.requested == 2
    assert result.processed == 2
    assert db_session.query(RiskSignal).count() == 2
