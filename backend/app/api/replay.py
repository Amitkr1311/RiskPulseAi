from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.ingestion import _ingestion_key_guard
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.replay.service import ReplayManager, ReplayStateError
from app.schemas.replay import ReplayStartRequest, ReplayStatusRead

router = APIRouter(prefix="/replay", tags=["historical social replay"])
replay_manager = ReplayManager()


@router.get("/status", response_model=ReplayStatusRead)
def get_replay_status(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ReplayStatusRead:
    return replay_manager.status(db, settings)


@router.post("/start", response_model=ReplayStatusRead, dependencies=[Depends(_ingestion_key_guard)])
def start_replay(
    payload: ReplayStartRequest | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ReplayStatusRead:
    request = payload or ReplayStartRequest(
        speed_records_per_second=settings.replay_default_speed,
        batch_size=settings.replay_default_batch_size,
    )
    return _transition(lambda: replay_manager.start(db, settings, request.speed_records_per_second, request.batch_size))


@router.post("/pause", response_model=ReplayStatusRead, dependencies=[Depends(_ingestion_key_guard)])
def pause_replay(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ReplayStatusRead:
    return _transition(lambda: replay_manager.pause(db, settings))


@router.post("/resume", response_model=ReplayStatusRead, dependencies=[Depends(_ingestion_key_guard)])
def resume_replay(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ReplayStatusRead:
    return _transition(lambda: replay_manager.resume(db, settings))


@router.post("/stop", response_model=ReplayStatusRead, dependencies=[Depends(_ingestion_key_guard)])
def stop_replay(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ReplayStatusRead:
    return _transition(lambda: replay_manager.stop(db, settings))


@router.post("/reset", response_model=ReplayStatusRead, dependencies=[Depends(_ingestion_key_guard)])
def reset_replay(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ReplayStatusRead:
    return _transition(lambda: replay_manager.reset(db, settings))


def _transition(action):
    try:
        return action()
    except ReplayStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
