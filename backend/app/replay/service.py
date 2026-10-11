from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from threading import Event, RLock, Thread
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import SocialReplayState
from app.db.session import SessionLocal
from app.ingestion.adapters.social import SocialCsvAdapter
from app.ingestion.errors import ProviderError
from app.ingestion.normalization import parse_timestamp
from app.ingestion.service import IngestionService
from app.nlp.service import NLPService
from app.schemas.replay import ReplayStatusRead

logger = logging.getLogger("riskpulse.replay")


class ReplayStateError(ValueError):
    pass


class ReplayManager:
    """Own one bounded worker for the persisted historical social replay cursor."""

    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
        adapter_factory: Callable[[Settings], SocialCsvAdapter] = SocialCsvAdapter,
    ) -> None:
        self.session_factory = session_factory
        self.adapter_factory = adapter_factory
        self._lock = RLock()
        self._stop_event = Event()
        self._worker: Thread | None = None

    def status(self, db: Session, settings: Settings) -> ReplayStatusRead:
        adapter = self.adapter_factory(settings)
        state = self._ensure_state(db, adapter)
        return self._read(state, adapter.configured)

    def start(self, db: Session, settings: Settings, speed: float, batch_size: int) -> ReplayStatusRead:
        if speed > settings.replay_max_speed:
            raise ReplayStateError(f"Replay speed cannot exceed {settings.replay_max_speed:g} records/second")
        adapter = self.adapter_factory(settings)
        if not adapter.configured:
            state = self._ensure_state(db, adapter)
            state.status = "error"
            state.last_error = f"Social CSV not found at {settings.social_csv_path}"
            db.commit()
            raise ReplayStateError(state.last_error)

        with self._lock:
            state = self._ensure_state(db, adapter)
            if state.status == "running":
                return self._read(state, True)
            if state.status == "paused":
                raise ReplayStateError("Replay is paused; use resume instead")

            if state.status == "completed":
                self._reset_counters(state)
            if state.status not in {"idle", "stopped", "error"}:
                raise ReplayStateError(f"Replay cannot start from state '{state.status}'")

            try:
                state.total_records = adapter.count_records()
            except ProviderError as exc:
                state.status = "error"
                state.last_error = str(exc)[:500]
                db.commit()
                raise ReplayStateError(str(exc)) from exc
            if state.total_records == 0:
                state.status = "completed"
                state.completed_at = datetime.now(UTC)
                state.last_error = "The social CSV contains no data rows"
                db.commit()
                return self._read(state, True)

            state.dataset_path = str(adapter.path)
            state.status = "running"
            state.speed_records_per_second = Decimal(str(speed))
            state.batch_size = batch_size
            state.started_at = state.started_at or datetime.now(UTC)
            state.completed_at = None
            state.last_error = None
            db.commit()
            self._spawn_locked(settings)
            return self._read(state, True)

    def pause(self, db: Session, settings: Settings) -> ReplayStatusRead:
        with self._lock:
            adapter = self.adapter_factory(settings)
            state = self._ensure_state(db, adapter)
            if state.status != "running":
                raise ReplayStateError(f"Replay can only be paused while running, not '{state.status}'")
            state.status = "paused"
            db.commit()
            return self._read(state, adapter.configured)

    def resume(self, db: Session, settings: Settings) -> ReplayStatusRead:
        with self._lock:
            adapter = self.adapter_factory(settings)
            state = self._ensure_state(db, adapter)
            if state.status != "paused":
                raise ReplayStateError(f"Replay can only be resumed while paused, not '{state.status}'")
            state.status = "running"
            state.last_error = None
            db.commit()
            self._spawn_locked(settings)
            return self._read(state, adapter.configured)

    def stop(self, db: Session, settings: Settings) -> ReplayStatusRead:
        with self._lock:
            adapter = self.adapter_factory(settings)
            state = self._ensure_state(db, adapter)
            if state.status not in {"running", "paused"}:
                raise ReplayStateError(f"Replay can only be stopped while running or paused, not '{state.status}'")
            state.status = "stopped"
            db.commit()
            self._stop_event.set()
            return self._read(state, adapter.configured)

    def reset(self, db: Session, settings: Settings) -> ReplayStatusRead:
        with self._lock:
            adapter = self.adapter_factory(settings)
            state = self._ensure_state(db, adapter)
            if state.status in {"running", "paused"}:
                raise ReplayStateError("Stop the replay before resetting it")
            self._reset_counters(state)
            state.dataset_path = str(adapter.path)
            state.status = "idle"
            state.last_error = None
            db.commit()
            return self._read(state, adapter.configured)

    def process_batch(self, db: Session, settings: Settings) -> bool:
        """Process one batch; exposed for deterministic tests and used by the worker."""
        adapter = self.adapter_factory(settings)
        state = self._ensure_state(db, adapter)
        if state.status != "running":
            return False
        if state.current_position >= state.total_records:
            state.status = "completed"
            state.completed_at = datetime.now(UTC)
            db.commit()
            return False

        try:
            records = [dict(record) for record in adapter.fetch(state.batch_size, state.current_position)]
            if not records:
                state.status = "completed"
                state.completed_at = datetime.now(UTC)
                db.commit()
                return False

            result = IngestionService(db, {"social": adapter}, settings).run_records("social", records)
            nlp_result = NLPService(db, settings).process_articles(result.inserted_article_ids)
            # A control endpoint may have changed the state while this batch was
            # being processed. Refresh before writing counters so stop/pause is
            # never overwritten by a stale worker object.
            db.refresh(state)
            state.records_attempted += len(records)
            state.records_inserted += result.inserted
            state.duplicates_skipped += result.duplicates_skipped
            state.records_failed += result.failed + nlp_result.failed
            state.current_position += len(records)
            state.last_record_at = self._last_record_timestamp(records) or datetime.now(UTC)
            state.last_error = None if not result.error_category else result.error_category
            if state.status == "running" and state.current_position >= state.total_records:
                state.status = "completed"
                state.completed_at = datetime.now(UTC)
            db.commit()
            return state.status == "running"
        except ProviderError as exc:
            db.rollback()
            self._mark_error(db, str(exc))
            return False
        except Exception:
            db.rollback()
            logger.exception("Historical social replay batch failed")
            self._mark_error(db, "Replay batch failed; inspect backend logs and retry from the saved position")
            return False

    def recover_after_restart(self) -> None:
        """Running workers cannot survive a process restart; preserve the cursor safely."""
        db = self.session_factory()
        try:
            state = db.scalar(select(SocialReplayState).where(SocialReplayState.id == 1))
            if state is not None and state.status == "running":
                state.status = "stopped"
                state.last_error = "Backend restarted; replay stopped at the saved position"
                db.commit()
        except Exception:
            db.rollback()
            logger.warning("Replay recovery skipped because replay state is unavailable", exc_info=True)
        finally:
            db.close()

    def shutdown(self) -> None:
        with self._lock:
            self._stop_event.set()
            worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=5)
        with self._lock:
            self._worker = None

    def _spawn_locked(self, settings: Settings) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop_event = Event()
        self._worker = Thread(target=self._worker_loop, args=(settings,), daemon=True, name="social-replay")
        self._worker.start()

    def _worker_loop(self, settings: Settings) -> None:
        try:
            while not self._stop_event.is_set():
                db = self.session_factory()
                try:
                    should_continue = self.process_batch(db, settings)
                    if not should_continue:
                        return
                    state = db.scalar(select(SocialReplayState).where(SocialReplayState.id == 1))
                    speed = float(state.speed_records_per_second) if state is not None else 1.0
                    batch_size = state.batch_size if state is not None else 1
                finally:
                    db.close()
                self._stop_event.wait(max(0.01, batch_size / speed))
        finally:
            with self._lock:
                self._worker = None

    def _ensure_state(self, db: Session, adapter: SocialCsvAdapter) -> SocialReplayState:
        state = db.scalar(select(SocialReplayState).where(SocialReplayState.id == 1))
        if state is None:
            state = SocialReplayState(
                id=1,
                dataset_path=str(adapter.path),
                status="idle",
                batch_size=1,
                speed_records_per_second=Decimal("1"),
            )
            db.add(state)
            db.commit()
            db.refresh(state)
        return state

    @staticmethod
    def _reset_counters(state: SocialReplayState) -> None:
        state.status = "idle"
        state.total_records = 0
        state.records_attempted = 0
        state.records_inserted = 0
        state.duplicates_skipped = 0
        state.records_failed = 0
        state.current_position = 0
        state.started_at = None
        state.last_record_at = None
        state.completed_at = None
        state.last_error = None

    @staticmethod
    def _last_record_timestamp(records: list[dict[str, object]]) -> datetime | None:
        timestamps: list[datetime] = []
        for record in records:
            try:
                value = parse_timestamp(record.get("published_at"))
            except Exception:
                continue
            if value is not None:
                timestamps.append(value)
        return max(timestamps) if timestamps else None

    @staticmethod
    def _mark_error(db: Session, message: str) -> None:
        state = db.scalar(select(SocialReplayState).where(SocialReplayState.id == 1))
        if state is not None:
            state.status = "error"
            state.last_error = message[:500]
            db.commit()

    @staticmethod
    def _read(state: SocialReplayState, configured: bool) -> ReplayStatusRead:
        percentage = 0.0
        if state.total_records:
            percentage = round(min(100, state.current_position / state.total_records * 100), 2)
        return ReplayStatusRead(
            dataset=state.dataset_path,
            configured=configured,
            status=state.status,
            total_records=state.total_records,
            records_attempted=state.records_attempted,
            records_inserted=state.records_inserted,
            duplicates_skipped=state.duplicates_skipped,
            records_failed=state.records_failed,
            current_position=state.current_position,
            speed_records_per_second=float(state.speed_records_per_second),
            batch_size=state.batch_size,
            progress_percentage=percentage,
            started_at=state.started_at,
            last_record_at=state.last_record_at,
            completed_at=state.completed_at,
            last_error=state.last_error,
        )
