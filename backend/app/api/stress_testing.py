from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.stress_testing import (
    SignalStressRunRequest,
    StressEligibilityRead,
    StressRunDetail,
    StressRunPage,
    StressRunRequest,
    StressScenarioRead,
)
from app.stress_testing.errors import (
    StressIneligibleSignalError,
    StressPortfolioNotFoundError,
    StressRunNotFoundError,
    StressScenarioNotFoundError,
    StressSignalNotFoundError,
    StressValidationError,
)
from app.stress_testing.service import StressTestingService

router = APIRouter(prefix="/stress-testing", tags=["stress-testing"])


@router.get("/scenarios", response_model=list[StressScenarioRead])
def list_scenarios(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> list[StressScenarioRead]:
    return StressTestingService(db, settings).scenarios()


@router.post("/run", response_model=StressRunDetail)
def run_stress_test(
    payload: StressRunRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StressRunDetail:
    try:
        result, _reused = StressTestingService(db, settings).run(
            portfolio_id=payload.portfolio_id,
            scenario_id=payload.scenario_id,
            risk_signal_id=payload.risk_signal_id,
            trigger_mode=payload.trigger_mode,
            fresh_run=payload.fresh_run,
        )
        return result
    except Exception as exc:
        _raise_stress_http_error(exc)
        raise AssertionError("unreachable")


@router.post("/signals/{signal_id}/run", response_model=StressRunDetail)
def run_signal_stress_test(
    signal_id: int,
    payload: SignalStressRunRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StressRunDetail:
    service = StressTestingService(db, settings)
    try:
        eligibility = service.eligibility_for_signal(signal_id, payload.portfolio_id)
        scenario_id = payload.scenario_id or (eligibility.matching_scenarios[0] if eligibility.matching_scenarios else "")
        if not scenario_id:
            raise StressIneligibleSignalError(eligibility.reasons or ["unsupported_event_type"])
        result, _reused = service.run(
            portfolio_id=payload.portfolio_id,
            scenario_id=scenario_id,
            risk_signal_id=signal_id,
            trigger_mode="manual",
            fresh_run=payload.fresh_run,
        )
        return result
    except Exception as exc:
        _raise_stress_http_error(exc)
        raise AssertionError("unreachable")


@router.get("/runs", response_model=StressRunPage)
def list_stress_runs(
    portfolio_id: int | None = Query(default=None, ge=1),
    scenario_id: str | None = Query(default=None, min_length=1, max_length=64),
    run_status: str | None = Query(default=None, alias="status", min_length=1, max_length=32),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100_000),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StressRunPage:
    try:
        return StressTestingService(db, settings).list_runs(
            portfolio_id=portfolio_id,
            scenario_id=scenario_id,
            status=run_status,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        _raise_stress_http_error(exc)
        raise AssertionError("unreachable")


@router.get("/runs/{simulation_id}", response_model=StressRunDetail)
def get_stress_run(
    simulation_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StressRunDetail:
    try:
        return StressTestingService(db, settings).detail(simulation_id)
    except Exception as exc:
        _raise_stress_http_error(exc)
        raise AssertionError("unreachable")


@router.get("/signals/{signal_id}/eligibility", response_model=StressEligibilityRead)
def signal_eligibility(
    signal_id: int,
    portfolio_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StressEligibilityRead:
    try:
        return StressTestingService(db, settings).eligibility_for_signal(signal_id, portfolio_id)
    except Exception as exc:
        _raise_stress_http_error(exc)
        raise AssertionError("unreachable")


def _raise_stress_http_error(exc: Exception) -> None:
    if isinstance(exc, SQLAlchemyError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service is unavailable") from exc
    if isinstance(exc, (StressScenarioNotFoundError, StressPortfolioNotFoundError, StressSignalNotFoundError, StressRunNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": exc.code, "message": str(exc)}) from exc
    if isinstance(exc, StressIneligibleSignalError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": exc.code, "reasons": exc.reasons, "message": "Risk signal is not eligible for this stress simulation"}) from exc
    if isinstance(exc, StressValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": exc.code, "message": str(exc)}) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stress simulation service is unavailable") from exc
