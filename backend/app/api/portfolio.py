from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.portfolio import PortfolioPositionPage, PortfolioPositionRead, PortfolioRead, PortfolioSummary
from app.services.portfolio import PortfolioNotFoundError, PortfolioService, PositionNotFoundError

router = APIRouter(prefix="/portfolio", tags=["portfolio"])
ASSET_TYPES = {"corporate_loan", "government_bond", "corporate_bond", "equity", "derivative"}


@router.get(
    "",
    response_model=PortfolioRead,
    summary="Get the synthetic portfolio",
    description="Returns the stable demo portfolio metadata and a database-derived base valuation summary.",
    responses={404: {"description": "Portfolio not found"}},
)
def get_portfolio(
    portfolio_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> PortfolioRead:
    try:
        return PortfolioService(db).portfolio_read(portfolio_id)
    except PortfolioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/positions",
    response_model=PortfolioPositionPage,
    summary="List synthetic portfolio positions",
    description="Returns explicit INR and crore units with stable pagination and asset-class/sector filters.",
    responses={404: {"description": "Portfolio not found"}},
)
def list_positions(
    portfolio_id: int | None = Query(default=None, ge=1),
    asset_class: str | None = Query(default=None, min_length=1, max_length=64),
    sector: str | None = Query(default=None, min_length=1, max_length=128),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100_000),
    db: Session = Depends(get_db),
) -> PortfolioPositionPage:
    normalized_asset_class = asset_class.strip().casefold() if asset_class else None
    if normalized_asset_class is not None and normalized_asset_class not in ASSET_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported asset_class")
    try:
        return PortfolioService(db).list_positions(
            portfolio_id=portfolio_id,
            asset_type=normalized_asset_class,
            sector=sector,
            limit=limit,
            offset=offset,
        )
    except PortfolioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/positions/{position_id}",
    response_model=PortfolioPositionRead,
    summary="Get one portfolio position",
    responses={404: {"description": "Position not found"}},
)
def get_position(position_id: int, db: Session = Depends(get_db)) -> PortfolioPositionRead:
    try:
        return PortfolioService(db).get_position(position_id)
    except PositionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/summary",
    response_model=PortfolioSummary,
    summary="Get portfolio valuation and allocation summary",
    description="Calculates totals and allocations from persisted positions without applying stress shocks.",
    responses={404: {"description": "Portfolio not found"}},
)
def get_portfolio_summary(
    portfolio_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> PortfolioSummary:
    try:
        return PortfolioService(db).summary(portfolio_id)
    except PortfolioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
