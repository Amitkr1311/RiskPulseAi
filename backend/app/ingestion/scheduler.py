import asyncio
import logging
from collections.abc import Callable

from app.core.config import Settings
from app.db.session import SessionLocal
from app.ingestion.factory import build_adapters
from app.ingestion.service import IngestionService
from app.nlp.service import NLPService

logger = logging.getLogger("riskpulse.ingestion.scheduler")
SUPPORTED_LIVE_SOURCES = frozenset({"news", "social", "reddit"})


class LiveIngestionScheduler:
    """Poll configured provider adapters and process new articles in the API process."""

    def __init__(
        self,
        settings: Settings,
        session_factory: Callable = SessionLocal,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory

    @property
    def sources(self) -> list[str]:
        adapters = build_adapters(self.settings)
        return [
            source
            for source in self.settings.ingestion_live_sources
            if source in SUPPORTED_LIVE_SOURCES
            and (source != "reddit" or self.settings.reddit_ingestion_enabled)
            and (source != "social" or adapters["social"].configured)
        ]

    def run_once(self) -> None:
        sources = self.sources
        if not sources:
            logger.warning("Live ingestion is enabled but no supported sources are configured")
            return

        db = self.session_factory()
        try:
            adapters = build_adapters(self.settings)
            results = IngestionService(db, adapters, self.settings).run(sources)
            logger.info(
                "Live ingestion poll completed",
                extra={
                    "sources": sources,
                    "inserted": sum(result.inserted for result in results),
                    "failed": sum(result.failed for result in results),
                },
            )
            if self.settings.ingestion_live_process_nlp:
                result = NLPService(db, self.settings).process_pending()
                logger.info(
                    "Live NLP processing completed",
                    extra={"processed": result.processed, "failed": result.failed},
                )
        except Exception:
            db.rollback()
            logger.exception("Live ingestion poll failed")
        finally:
            db.close()

    async def run(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            await asyncio.to_thread(self.run_once)
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=self.settings.ingestion_poll_interval_seconds,
                )
            except asyncio.TimeoutError:
                continue
