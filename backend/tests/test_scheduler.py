from app.core.config import Settings
from app.ingestion.scheduler import LiveIngestionScheduler


def test_live_scheduler_only_selects_supported_configured_sources() -> None:
    settings = Settings(ingestion_live_sources=["reddit", "demo", "news", "unknown"])

    scheduler = LiveIngestionScheduler(settings)

    assert scheduler.sources == ["news"]


def test_live_scheduler_includes_reddit_when_explicitly_enabled() -> None:
    settings = Settings(
        ingestion_live_sources=["reddit", "demo", "news", "unknown"],
        reddit_ingestion_enabled=True,
    )

    scheduler = LiveIngestionScheduler(settings)

    assert scheduler.sources == ["reddit", "news"]
