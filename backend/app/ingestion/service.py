import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from collections.abc import Mapping
from typing import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Article, IngestionRun
from app.ingestion.adapters.base import SourceAdapter
from app.ingestion.errors import ProviderError, ProviderValidationError
from app.ingestion.normalization import NormalizedArticle

logger = logging.getLogger("riskpulse.ingestion")


@dataclass(frozen=True)
class SourceRunResult:
    run_id: int
    source: str
    status: str
    fetched: int
    inserted: int
    duplicates_skipped: int
    failed: int
    error_category: str | None
    inserted_article_ids: tuple[int, ...] = ()


class IngestionService:
    def __init__(
        self,
        db: Session,
        adapters: dict[str, SourceAdapter],
        settings: Settings,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.db = db
        self.adapters = adapters
        self.settings = settings
        self.sleep = sleep

    def run(self, sources: list[str], limit: int | None = None, offset: int = 0) -> list[SourceRunResult]:
        batch_limit = limit or self.settings.ingestion_batch_size
        return [self.run_source(source, batch_limit, offset) for source in sources]

    def run_source(self, source: str, limit: int, offset: int = 0) -> SourceRunResult:
        adapter = self.adapters.get(source)
        run = self._start_run(source)

        logger.info(
            "Ingestion started",
            extra={"source": source, "ingestion_run_id": run.id, "started_at": run.started_at.isoformat()},
        )

        if adapter is None:
            return self._complete_run(
                run.id,
                status="failed",
                error_category="unknown_source",
                message="configured source adapter is unavailable",
            )

        try:
            records = self._fetch_with_retries(adapter, limit, run.id, offset)
        except ProviderError as exc:
            status = "disabled" if exc.category == "not_configured" else "failed"
            return self._complete_run(run.id, status=status, error_category=exc.category, message=str(exc))

        return self._persist_records(run.id, source, adapter, records)

    def run_records(self, source: str, records: list[Mapping[str, object]]) -> SourceRunResult:
        """Persist adapter-fetched records through the normal dedupe/normalization flow."""
        adapter = self.adapters.get(source)
        run = self._start_run(source)
        if adapter is None:
            return self._complete_run(
                run.id,
                status="failed",
                error_category="unknown_source",
                message="configured source adapter is unavailable",
            )
        return self._persist_records(run.id, source, adapter, records)

    def _start_run(self, source: str) -> IngestionRun:
        run = IngestionRun(source=source, status="running", started_at=datetime.now(UTC))
        self.db.add(run)
        self.db.flush()
        self.db.commit()
        return run

    def _persist_records(
        self,
        run_id: int,
        source: str,
        adapter: SourceAdapter,
        records: list[Mapping[str, object]],
    ) -> SourceRunResult:
        inserted = 0
        duplicates_skipped = 0
        failed = 0
        error_category: str | None = None
        inserted_article_ids: list[int] = []
        for record in records:
            try:
                normalized = adapter.normalize(record)
                article = self._insert_if_new(normalized)
                if article is not None:
                    inserted += 1
                    inserted_article_ids.append(article.id)
                else:
                    duplicates_skipped += 1
            except ProviderValidationError as exc:
                failed += 1
                error_category = exc.category
            except (TypeError, ValueError) as exc:
                failed += 1
                error_category = "validation"
                logger.warning(
                    "Record validation failed",
                    extra={"source": source, "ingestion_run_id": run_id, "error_category": error_category},
                )
            except SQLAlchemyError:
                self.db.rollback()
                return self._complete_run(
                    run_id,
                    status="failed",
                    fetched=len(records),
                    inserted=inserted,
                    duplicates_skipped=duplicates_skipped,
                    failed=failed + 1,
                    error_category="database",
                    message="database persistence failed",
                )

        return self._complete_run(
            run_id,
            status="completed" if failed == 0 else "completed_with_errors",
            fetched=len(records),
            inserted=inserted,
            duplicates_skipped=duplicates_skipped,
            failed=failed,
            error_category=error_category,
            inserted_article_ids=tuple(inserted_article_ids),
        )

    def _fetch_with_retries(self, adapter: SourceAdapter, limit: int, run_id: int, offset: int) -> list[dict[str, object]]:
        for attempt in range(self.settings.ingestion_max_retries + 1):
            try:
                return [dict(record) for record in adapter.fetch(limit, offset)]
            except ProviderError as exc:
                if not exc.retryable or attempt >= self.settings.ingestion_max_retries:
                    raise
                delay = self.settings.ingestion_retry_backoff_seconds * (2**attempt)
                logger.warning(
                    "Retrying provider fetch",
                    extra={
                        "source": adapter.source_name,
                        "ingestion_run_id": run_id,
                        "attempt": attempt + 1,
                        "error_category": exc.category,
                    },
                )
                self.sleep(delay)
        raise RuntimeError("retry loop exited unexpectedly")

    def _insert_if_new(self, normalized: NormalizedArticle) -> Article | None:
        duplicate_query = select(Article.id).where(Article.source == normalized.source)
        if normalized.external_id:
            duplicate_query = duplicate_query.where(Article.external_id == normalized.external_id)
        else:
            duplicate_query = duplicate_query.where(Article.content_hash == normalized.content_hash)
        if self.db.scalar(duplicate_query.limit(1)) is not None:
            return None

        article = Article(**normalized.model_dump())
        try:
            with self.db.begin_nested():
                self.db.add(article)
                self.db.flush()
        except IntegrityError:
            return None
        return article

    def _complete_run(
        self,
        run_id: int,
        *,
        status: str,
        fetched: int = 0,
        inserted: int = 0,
        duplicates_skipped: int = 0,
        failed: int = 0,
        error_category: str | None = None,
        message: str | None = None,
        inserted_article_ids: tuple[int, ...] = (),
    ) -> SourceRunResult:
        run = self.db.get(IngestionRun, run_id)
        if run is None:
            raise RuntimeError("ingestion run disappeared before completion")
        run.status = status
        run.records_seen = fetched
        run.records_created = inserted
        run.duplicates_skipped = duplicates_skipped
        run.records_failed = failed
        run.error_category = error_category
        run.error_message = message
        run.completed_at = datetime.now(UTC)
        self.db.commit()
        logger.info(
            "Ingestion completed",
            extra={
                "source": run.source,
                "ingestion_run_id": run.id,
                "completed_at": run.completed_at.isoformat(),
                "records_fetched": fetched,
                "records_inserted": inserted,
                "duplicates_skipped": duplicates_skipped,
                "records_failed": failed,
                "error_category": error_category,
            },
        )
        return SourceRunResult(
            run_id=run.id,
            source=run.source,
            status=run.status,
            fetched=run.records_seen,
            inserted=run.records_created,
            duplicates_skipped=run.duplicates_skipped,
            failed=run.records_failed,
            error_category=run.error_category,
            inserted_article_ids=inserted_article_ids,
        )
