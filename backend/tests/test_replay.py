from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.db.models import Article, SocialReplayState
from app.replay.service import ReplayManager, ReplayStateError


FIXTURE = Path(__file__).parent / "fixtures" / "social-replay.csv"


class SynchronousReplayManager(ReplayManager):
    def _spawn_locked(self, settings: Settings) -> None:
        del settings


def _settings() -> Settings:
    return Settings(
        social_csv_path=str(FIXTURE),
        news_rss_url=None,
        reddit_access_token=None,
        ingestion_live_enabled=False,
        replay_max_speed=10,
    )


def _state(db_session, status: str = "idle") -> SocialReplayState:
    state = SocialReplayState(
        id=1,
        dataset_path=str(FIXTURE),
        status=status,
        speed_records_per_second=1,
        batch_size=2,
    )
    db_session.add(state)
    db_session.commit()
    return state


def test_replay_start_status_and_invalid_speed(db_session):
    manager = SynchronousReplayManager()
    status = manager.start(db_session, _settings(), speed=5, batch_size=2)

    assert status.status == "running"
    assert status.total_records == 4
    assert status.current_position == 0
    assert status.speed_records_per_second == 5

    with pytest.raises(ReplayStateError, match="cannot exceed"):
        manager.start(db_session, _settings(), speed=11, batch_size=2)


def test_replay_processes_in_batches_and_completes_with_accurate_counters(db_session):
    manager = SynchronousReplayManager()
    manager.start(db_session, _settings(), speed=10, batch_size=2)

    assert manager.process_batch(db_session, _settings()) is True
    first = manager.status(db_session, _settings())
    assert first.records_attempted == 2
    assert first.records_inserted == 2
    assert first.current_position == 2

    assert manager.process_batch(db_session, _settings()) is False
    result = manager.status(db_session, _settings())
    assert result.status == "completed"
    assert result.records_attempted == 4
    assert result.records_inserted == 2
    assert result.duplicates_skipped == 1
    assert result.records_failed == 1
    assert result.progress_percentage == 100

    articles = db_session.scalars(select(Article).order_by(Article.id)).all()
    assert len(articles) == 2
    assert all(article.source == "social" and article.is_historical for article in articles)
    assert all(article.source_metadata["replay"] is True for article in articles)
    assert articles[0].published_at.replace(tzinfo=UTC) == datetime(2024, 1, 2, 9, tzinfo=UTC)
    assert articles[0].ingested_at is not None


def test_replay_controls_have_safe_transitions_and_reset_preserves_articles(db_session):
    manager = SynchronousReplayManager()
    settings = _settings()
    manager.start(db_session, settings, speed=1, batch_size=1)
    manager.process_batch(db_session, settings)

    paused = manager.pause(db_session, settings)
    assert paused.status == "paused"
    with pytest.raises(ReplayStateError, match="paused"):
        manager.start(db_session, settings, speed=1, batch_size=1)
    resumed = manager.resume(db_session, settings)
    assert resumed.status == "running"
    stopped = manager.stop(db_session, settings)
    assert stopped.status == "stopped"

    reset = manager.reset(db_session, settings)
    assert reset.status == "idle"
    assert reset.current_position == 0
    assert db_session.scalar(select(Article.id)) is not None


def test_reset_is_rejected_while_replay_is_active(db_session):
    manager = SynchronousReplayManager()
    settings = _settings()
    manager.start(db_session, settings, speed=1, batch_size=1)

    with pytest.raises(ReplayStateError, match="Stop the replay"):
        manager.reset(db_session, settings)
