from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ZERO = Decimal("0")
ONE = Decimal("1")


class CorporateLoanParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basis: Literal["exposure"]
    borrower_group_id: str = Field(min_length=1, max_length=128)
    borrower: str | None = Field(default=None, max_length=255)
    issuer: str | None = Field(default=None, max_length=255)
    ticker: str | None = Field(default=None, max_length=32)
    sector: str = Field(min_length=1, max_length=128)
    pd: Decimal = Field(ge=ZERO, le=ONE)
    lgd: Decimal = Field(ge=ZERO, le=ONE)
    recovery_rate: Decimal | None = Field(default=None, ge=ZERO, le=ONE)
    remaining_tenor_years: Decimal | None = Field(default=None, ge=ZERO)

    @model_validator(mode="after")
    def validate_recovery(self) -> "CorporateLoanParameters":
        if self.recovery_rate is not None and abs(self.recovery_rate - (ONE - self.lgd)) > Decimal("0.0001"):
            raise ValueError("recovery_rate must equal 1 - lgd")
        return self


class GovernmentBondParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basis: Literal["market_value"]
    issuer: str = Field(min_length=1, max_length=255)
    maturity_year: int = Field(ge=1900, le=2200)
    modified_duration: Decimal = Field(ge=ZERO)
    convexity: Decimal | None = Field(default=None, ge=ZERO)
    baseline_yield: Decimal = Field(ge=ZERO, le=ONE)
    yield_unit: Literal["decimal_rate"]


class CorporateBondParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basis: Literal["market_value"]
    issuer: str = Field(min_length=1, max_length=255)
    borrower: str | None = Field(default=None, max_length=255)
    ticker: str | None = Field(default=None, max_length=32)
    sector: str = Field(min_length=1, max_length=128)
    credit_rating: str = Field(min_length=1, max_length=16)
    modified_duration: Decimal = Field(ge=ZERO)
    convexity: Decimal | None = Field(default=None, ge=ZERO)
    credit_spread_duration: Decimal = Field(ge=ZERO)
    baseline_credit_spread: Decimal = Field(ge=ZERO)
    spread_unit: Literal["decimal_rate"]


class EquityParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basis: Literal["market_value"]
    ticker: str = Field(min_length=1, max_length=32)
    instrument_name: str = Field(min_length=1, max_length=255)
    sector: str = Field(min_length=1, max_length=128)
    beta: Decimal
    market_reference: str | None = Field(default=None, max_length=255)


class DerivativeParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basis: Literal["simplified_mark_to_market"]
    instrument_type: str = Field(min_length=1, max_length=128)
    underlying: str = Field(min_length=1, max_length=128)
    notional_exposure_inr: Decimal = Field(ge=ZERO)
    delta_equivalent: Decimal | None = None
    market_value_definition: Literal["simplified_mark_to_market_portfolio_value"]
    derivative_kind: Literal["interest_rate_swap", "fx_forward", "index_total_return_swap"] | None = None
    tenor_years: Decimal | None = Field(default=None, gt=ZERO)
    duration_years: Decimal | None = Field(default=None, gt=ZERO)
    fixed_rate: Decimal | None = Field(default=None, ge=ZERO, le=ONE)
    floating_rate: Decimal | None = Field(default=None, ge=ZERO, le=ONE)
    rate_unit: Literal["decimal_rate"] | None = None
    pay_receive: Literal["pay_fixed", "receive_fixed"] | None = None
    fx_pair: str | None = Field(default=None, min_length=3, max_length=16)
    notional_currency: str | None = Field(default=None, min_length=3, max_length=3)
    forward_fx_rate: Decimal | None = Field(default=None, gt=ZERO)
    spot_fx_rate: Decimal | None = Field(default=None, gt=ZERO)

    @model_validator(mode="after")
    def validate_derivative_kind(self) -> "DerivativeParameters":
        kind = self.derivative_kind or self.instrument_type.casefold()
        if kind in {"interest_rate_swap", "irs"}:
            if self.tenor_years is None or self.fixed_rate is None or self.floating_rate is None:
                raise ValueError("interest rate swaps require tenor and fixed/floating rates")
            if self.rate_unit != "decimal_rate":
                raise ValueError("interest rate swaps require rate_unit=decimal_rate")
        elif kind in {"fx_forward", "forward"}:
            if self.tenor_years is None or self.fx_pair is None or self.forward_fx_rate is None:
                raise ValueError("FX forwards require tenor, pair, and forward FX rate")
            if self.notional_currency is None:
                raise ValueError("FX forwards require a notional currency")
        elif self.delta_equivalent is None:
            raise ValueError("legacy derivatives require delta_equivalent")
        return self


PARAMETER_MODELS: dict[str, type[BaseModel]] = {
    "corporate_loan": CorporateLoanParameters,
    "government_bond": GovernmentBondParameters,
    "corporate_bond": CorporateBondParameters,
    "equity": EquityParameters,
    "derivative": DerivativeParameters,
}


def validate_position_parameters(asset_type: str, parameters: dict[str, Any]) -> BaseModel:
    model = PARAMETER_MODELS.get(asset_type)
    if model is None:
        raise ValueError(f"Unsupported asset type: {asset_type}")
    return model.model_validate(parameters)


class PortfolioAllocation(BaseModel):
    asset_class: str
    market_value_inr: Decimal = Field(ge=ZERO)
    market_value_crore: Decimal = Field(ge=ZERO)
    allocation_percentage: Decimal = Field(ge=ZERO, le=Decimal("100"))


class SectorAllocation(BaseModel):
    sector: str
    market_value_inr: Decimal = Field(ge=ZERO)
    allocation_percentage: Decimal = Field(ge=ZERO, le=Decimal("100"))


class PortfolioPositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    portfolio_key: str
    position_key: str
    name: str
    asset_class: str
    currency: str
    market_value_inr: Decimal = Field(ge=ZERO)
    market_value_crore: Decimal = Field(ge=ZERO)
    contribution_percentage: Decimal = Field(ge=ZERO, le=Decimal("100"))
    sector: str | None
    borrower: str | None
    valuation_parameters: dict[str, Any]
    is_demo: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_parameters(self) -> "PortfolioPositionRead":
        validate_position_parameters(self.asset_class, self.valuation_parameters)
        return self


class PortfolioPositionPage(BaseModel):
    items: list[PortfolioPositionRead]
    total: int = Field(ge=0)
    limit: int
    offset: int


class PortfolioSummary(BaseModel):
    portfolio_id: int
    portfolio_key: str
    name: str
    currency: str
    total_market_value_inr: Decimal = Field(ge=ZERO)
    total_market_value_crore: Decimal = Field(ge=ZERO)
    position_count: int = Field(ge=0)
    asset_class_allocations: list[PortfolioAllocation]
    sector_allocations: list[SectorAllocation]
    is_demo: bool


class PortfolioRead(PortfolioSummary):
    description: str | None
    created_at: datetime
    updated_at: datetime
