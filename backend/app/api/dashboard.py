from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard import dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get dashboard summary metrics",
    description="Returns counts and timestamps calculated from persisted article, signal, and ingestion records.",
)
def get_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    return DashboardSummary.model_validate(dashboard_summary(db))
