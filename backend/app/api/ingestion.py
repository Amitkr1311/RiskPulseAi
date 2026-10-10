import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import IngestionRun
from app.db.session import get_db
from app.ingestion.adapters.demo import DemoAdapter
from app.ingestion.factory import build_adapters
from app.ingestion.service import IngestionService, SourceRunResult
from app.schemas.ingestion import (
    IngestionResponse,
    IngestionRunRead,
    IngestionRunRequest,
    IngestionStatusResponse,
    SourceRunSummary,
    SourceStatus,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _ingestion_key_guard(
    x_ingestion_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.ingestion_api_key is None:
        return
    expected = settings.ingestion_api_key.get_secret_value()
    if x_ingestion_key is None or not secrets.compare_digest(x_ingestion_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ingestion key")


@router.post("/run", response_model=IngestionResponse, dependencies=[Depends(_ingestion_key_guard)])
def run_ingestion(
    payload: IngestionRunRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestionResponse:
    service = IngestionService(db, build_adapters(settings), settings)
    results = service.run(list(payload.sources), payload.limit)
    return _response(results)


@router.post("/demo", response_model=IngestionResponse, dependencies=[Depends(_ingestion_key_guard)])
def run_demo_ingestion(
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestionResponse:
    service = IngestionService(db, {"demo": DemoAdapter()}, settings)
    return _response(service.run(["demo"], limit))


@router.get("/status", response_model=IngestionStatusResponse)
def ingestion_status(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestionStatusResponse:
    recent = db.scalars(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(20)).all()
    latest_by_source: dict[str, IngestionRun] = {}
    for run in recent:
        latest_by_source.setdefault(run.source, run)

    adapters = build_adapters(settings)
    source_statuses = [
        SourceStatus(
            source=source,
            configured=adapter.configured,
            last_run=_run_read(latest_by_source[source]) if source in latest_by_source else None,
        )
        for source, adapter in adapters.items()
    ]
    return IngestionStatusResponse(
        sources=source_statuses,
        recent_runs=[_run_read(run) for run in recent],
    )


def _response(results: list[SourceRunResult]) -> IngestionResponse:
    return IngestionResponse(
        runs=[
            SourceRunSummary(
                run_id=result.run_id,
                source=result.source,
                status=result.status,
                fetched=result.fetched,
                inserted=result.inserted,
                duplicates_skipped=result.duplicates_skipped,
                failed=result.failed,
                error_category=result.error_category,
            )
            for result in results
        ],
        fetched=sum(result.fetched for result in results),
        inserted=sum(result.inserted for result in results),
        duplicates_skipped=sum(result.duplicates_skipped for result in results),
        failed=sum(result.failed for result in results),
    )


def _run_read(run: IngestionRun) -> IngestionRunRead:
    return IngestionRunRead(
        run_id=run.id,
        source=run.source,
        status=run.status,
        records_seen=run.records_seen,
        records_created=run.records_created,
        duplicates_skipped=run.duplicates_skipped,
        records_failed=run.records_failed,
        error_category=run.error_category,
        started_at=_as_utc(run.started_at),
        completed_at=_as_utc(run.completed_at) if run.completed_at else None,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

