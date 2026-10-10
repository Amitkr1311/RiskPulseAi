from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Portfolio, PortfolioPosition
from app.schemas.portfolio import (
    PortfolioAllocation,
    PortfolioPositionPage,
    PortfolioPositionRead,
    PortfolioRead,
    PortfolioSummary,
    SectorAllocation,
    validate_position_parameters,
)

DEMO_PORTFOLIO_KEY = "demo-banking-portfolio"
CRORE_INR = Decimal("10000000")
ONE_HUNDRED = Decimal("100")


class PortfolioNotFoundError(LookupError):
    pass


class PositionNotFoundError(LookupError):
    pass


class PortfolioService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_portfolio(self, portfolio_id: int | None = None) -> Portfolio:
        portfolio = (
            self.db.get(Portfolio, portfolio_id)
            if portfolio_id is not None
            else self.db.scalar(select(Portfolio).where(Portfolio.portfolio_key == DEMO_PORTFOLIO_KEY))
        )
        if portfolio is None:
            raise PortfolioNotFoundError("Portfolio not found")
        return portfolio

    def summary(self, portfolio_id: int | None = None) -> PortfolioSummary:
        portfolio = self.get_portfolio(portfolio_id)
        positions = self._positions(portfolio.id)
        total = sum((position.market_value for position in positions), Decimal("0"))
        return PortfolioSummary(
            portfolio_id=portfolio.id,
            portfolio_key=portfolio.portfolio_key,
            name=portfolio.name,
            currency=portfolio.currency,
            total_market_value_inr=total,
            total_market_value_crore=total / CRORE_INR,
            position_count=len(positions),
            asset_class_allocations=self._asset_allocations(positions, total),
            sector_allocations=self._sector_allocations(positions, total),
            is_demo=portfolio.is_demo,
        )

    def portfolio_read(self, portfolio_id: int | None = None) -> PortfolioRead:
        portfolio = self.get_portfolio(portfolio_id)
        summary = self.summary(portfolio.id)
        return PortfolioRead(
            **summary.model_dump(),
            description=portfolio.description,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
        )

    def list_positions(
        self,
        *,
        portfolio_id: int | None,
        asset_type: str | None,
        sector: str | None,
        limit: int,
        offset: int,
    ) -> PortfolioPositionPage:
        portfolio = self.get_portfolio(portfolio_id)
        filters = [PortfolioPosition.portfolio_id == portfolio.id]
        if asset_type:
            filters.append(PortfolioPosition.asset_type == asset_type.strip().casefold())
        if sector:
            filters.append(PortfolioPosition.sector == sector.strip())
        total = int(self.db.scalar(select(func.count()).select_from(PortfolioPosition).where(*filters)) or 0)
        positions = self.db.scalars(
            select(PortfolioPosition)
            .options(joinedload(PortfolioPosition.portfolio))
            .where(*filters)
            .order_by(PortfolioPosition.position_key.asc(), PortfolioPosition.id.asc())
            .offset(offset)
            .limit(limit)
        ).all()
        portfolio_total = self._total_for_portfolio(portfolio.id)
        return PortfolioPositionPage(
            items=[self.position_read(position, portfolio_total) for position in positions],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_position(self, position_id: int) -> PortfolioPositionRead:
        position = self.db.scalar(
            select(PortfolioPosition)
            .options(joinedload(PortfolioPosition.portfolio))
            .where(PortfolioPosition.id == position_id)
        )
        if position is None:
            raise PositionNotFoundError("Portfolio position not found")
        return self.position_read(position, self._total_for_portfolio(position.portfolio_id))

    def position_read(self, position: PortfolioPosition, portfolio_total: Decimal) -> PortfolioPositionRead:
        parameters = validate_position_parameters(position.asset_type, position.valuation_parameters)
        contribution = (
            position.market_value * ONE_HUNDRED / portfolio_total if portfolio_total else Decimal("0")
        )
        return PortfolioPositionRead(
            id=position.id,
            portfolio_id=position.portfolio_id,
            portfolio_key=position.portfolio.portfolio_key,
            position_key=position.position_key,
            name=position.name,
            asset_class=position.asset_type,
            currency=position.currency,
            market_value_inr=position.market_value,
            market_value_crore=position.market_value / CRORE_INR,
            contribution_percentage=contribution,
            sector=position.sector,
            borrower=position.borrower,
            valuation_parameters=parameters.model_dump(mode="json"),
            is_demo=position.is_demo,
            created_at=position.created_at,
            updated_at=position.updated_at,
        )

    def _positions(self, portfolio_id: int) -> list[PortfolioPosition]:
        return self.db.scalars(
            select(PortfolioPosition)
            .where(PortfolioPosition.portfolio_id == portfolio_id)
            .order_by(PortfolioPosition.position_key.asc(), PortfolioPosition.id.asc())
        ).all()

    def _total_for_portfolio(self, portfolio_id: int) -> Decimal:
        return self.db.scalar(
            select(func.coalesce(func.sum(PortfolioPosition.market_value), 0)).where(
                PortfolioPosition.portfolio_id == portfolio_id
            )
        ) or Decimal("0")

    @staticmethod
    def _asset_allocations(positions: list[PortfolioPosition], total: Decimal) -> list[PortfolioAllocation]:
        grouped: dict[str, Decimal] = {}
        for position in positions:
            grouped[position.asset_type] = grouped.get(position.asset_type, Decimal("0")) + position.market_value
        return [
            PortfolioAllocation(
                asset_class=asset_type,
                market_value_inr=value,
                market_value_crore=value / CRORE_INR,
                allocation_percentage=value * ONE_HUNDRED / total if total else Decimal("0"),
            )
            for asset_type, value in sorted(grouped.items())
        ]

    @staticmethod
    def _sector_allocations(positions: list[PortfolioPosition], total: Decimal) -> list[SectorAllocation]:
        grouped: dict[str, Decimal] = {}
        for position in positions:
            if position.sector:
                grouped[position.sector] = grouped.get(position.sector, Decimal("0")) + position.market_value
        return [
            SectorAllocation(
                sector=sector,
                market_value_inr=value,
                allocation_percentage=value * ONE_HUNDRED / total if total else Decimal("0"),
            )
            for sector, value in sorted(grouped.items())
        ]
