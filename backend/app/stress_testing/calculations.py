from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

from app.schemas.portfolio import (
    CorporateBondParameters,
    CorporateLoanParameters,
    DerivativeParameters,
    EquityParameters,
    GovernmentBondParameters,
)

MONEY_QUANTUM = Decimal("0.01")
FORMULA_VERSION = "stress-formulas-v1"


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def basis_points_to_decimal(value: Decimal) -> Decimal:
    return value / Decimal("10000")


@dataclass(frozen=True)
class ValuationResult:
    stressed_value: Decimal
    pnl: Decimal
    calculation_method: str
    explanation: str
    details: dict[str, Any]


def government_bond_valuation(
    base_value: Decimal,
    parameters: GovernmentBondParameters,
    yield_change_bps: Decimal,
) -> ValuationResult:
    delta_y = basis_points_to_decimal(yield_change_bps)
    duration_effect = -parameters.modified_duration * delta_y
    convexity_effect = (
        Decimal("0.5") * parameters.convexity * delta_y * delta_y
        if parameters.convexity is not None
        else Decimal("0")
    )
    price_change = duration_effect + convexity_effect
    stressed_value = money(max(Decimal("0"), base_value * (Decimal("1") + price_change)))
    pnl = money(stressed_value - base_value)
    return ValuationResult(
        stressed_value,
        pnl,
        "government_bond_modified_duration_convexity",
        "Government bond repricing uses ΔP/P ≈ -D_mod×Δy plus convexity when supplied; Δy is expressed as a decimal rate.",
        {
            "formula_version": FORMULA_VERSION,
            "base_value_inr": str(base_value),
            "yield_change_bps": str(yield_change_bps),
            "yield_change_decimal": str(delta_y),
            "modified_duration": str(parameters.modified_duration),
            "duration_effect": str(duration_effect),
            "convexity": str(parameters.convexity) if parameters.convexity is not None else None,
            "convexity_effect": str(convexity_effect),
            "price_change": str(price_change),
        },
    )


def corporate_bond_valuation(
    base_value: Decimal,
    parameters: CorporateBondParameters,
    benchmark_change_bps: Decimal,
    spread_change_bps: Decimal,
) -> ValuationResult:
    benchmark_change = basis_points_to_decimal(benchmark_change_bps)
    spread_change = basis_points_to_decimal(spread_change_bps)
    rate_effect = -parameters.modified_duration * benchmark_change
    spread_effect = -parameters.credit_spread_duration * spread_change
    convexity_effect = (
        Decimal("0.5") * parameters.convexity * benchmark_change * benchmark_change
        if parameters.convexity is not None
        else Decimal("0")
    )
    price_change = rate_effect + spread_effect + convexity_effect
    stressed_value = money(max(Decimal("0"), base_value * (Decimal("1") + price_change)))
    pnl = money(stressed_value - base_value)
    return ValuationResult(
        stressed_value,
        pnl,
        "corporate_bond_separate_rate_and_spread_duration",
        "Corporate bond repricing separates benchmark-rate duration and credit-spread duration; spread widening is applied once.",
        {
            "formula_version": FORMULA_VERSION,
            "base_value_inr": str(base_value),
            "benchmark_change_bps": str(benchmark_change_bps),
            "spread_change_bps": str(spread_change_bps),
            "benchmark_change_decimal": str(benchmark_change),
            "spread_change_decimal": str(spread_change),
            "rate_effect": str(rate_effect),
            "spread_effect": str(spread_effect),
            "convexity_effect": str(convexity_effect),
            "price_change": str(price_change),
        },
    )


def corporate_loan_valuation(
    base_value: Decimal,
    parameters: CorporateLoanParameters,
    pd_multiplier: Decimal,
) -> ValuationResult:
    stressed_pd = min(Decimal("1"), parameters.pd * pd_multiplier)
    baseline_ecl = base_value * parameters.pd * parameters.lgd
    stressed_ecl = base_value * stressed_pd * parameters.lgd
    incremental_loss = money(stressed_ecl - baseline_ecl)
    stressed_value = money(base_value - incremental_loss)
    pnl = money(stressed_value - base_value)
    return ValuationResult(
        stressed_value,
        pnl,
        "corporate_loan_incremental_ecl",
        "Corporate-loan P&L is the negative incremental ECL; principal exposure is not deducted a second time.",
        {
            "formula_version": FORMULA_VERSION,
            "base_exposure_inr": str(base_value),
            "baseline_pd": str(parameters.pd),
            "pd_multiplier": str(pd_multiplier),
            "stressed_pd": str(stressed_pd),
            "lgd": str(parameters.lgd),
            "baseline_ecl": str(money(baseline_ecl)),
            "stressed_ecl": str(money(stressed_ecl)),
            "incremental_credit_loss": str(incremental_loss),
        },
    )


def equity_valuation(base_value: Decimal, parameters: EquityParameters, return_shock: Decimal) -> ValuationResult:
    pnl = money(base_value * return_shock)
    stressed_value = money(base_value + pnl)
    return ValuationResult(
        stressed_value,
        money(stressed_value - base_value),
        "equity_return_shock",
        "Equity P&L equals market value multiplied by the applicable position return shock; beta is not applied a second time.",
        {
            "formula_version": FORMULA_VERSION,
            "base_value_inr": str(base_value),
            "return_shock": str(return_shock),
            "beta_reference_only": str(parameters.beta),
        },
    )


def interest_rate_swap_valuation(
    base_value: Decimal,
    parameters: DerivativeParameters,
    rate_shock_bps: Decimal,
) -> ValuationResult:
    duration = parameters.duration_years or parameters.tenor_years
    if duration is None:
        raise ValueError("interest rate swap duration is required")
    rate_shock = basis_points_to_decimal(rate_shock_bps)
    direction = Decimal("-1") if parameters.pay_receive == "receive_fixed" else Decimal("1")
    pnl = money(parameters.notional_exposure_inr * duration * rate_shock * direction)
    stressed_value = money(base_value + pnl)
    return ValuationResult(
        stressed_value,
        money(stressed_value - base_value),
        "interest_rate_swap_notional_duration_rate_shock",
        "Interest-rate swap P&L is approximated as notional × duration × rate shock; pay-fixed swaps gain when rates rise.",
        {
            "formula_version": FORMULA_VERSION,
            "base_market_value_inr": str(base_value),
            "notional_exposure_inr": str(parameters.notional_exposure_inr),
            "duration_years": str(duration),
            "rate_shock_bps": str(rate_shock_bps),
            "rate_shock_decimal": str(rate_shock),
            "pay_receive": parameters.pay_receive or "pay_fixed",
            "notional_duration_rate_change_inr": str(pnl),
        },
    )


def fx_forward_valuation(
    base_value: Decimal,
    parameters: DerivativeParameters,
    fx_return_shock: Decimal,
) -> ValuationResult:
    pnl = money(parameters.notional_exposure_inr * fx_return_shock)
    stressed_value = money(base_value + pnl)
    return ValuationResult(
        stressed_value,
        money(stressed_value - base_value),
        "fx_forward_notional_fx_shock",
        "FX-forward P&L is approximated as notional × the scenario FX return shock.",
        {
            "formula_version": FORMULA_VERSION,
            "base_market_value_inr": str(base_value),
            "notional_exposure_inr": str(parameters.notional_exposure_inr),
            "notional_currency": parameters.notional_currency,
            "fx_pair": parameters.fx_pair,
            "forward_fx_rate": str(parameters.forward_fx_rate),
            "spot_fx_rate": str(parameters.spot_fx_rate) if parameters.spot_fx_rate is not None else None,
            "fx_return_shock": str(fx_return_shock),
        },
    )


def derivative_valuation(
    base_value: Decimal,
    parameters: DerivativeParameters,
    underlying_return_shock: Decimal,
) -> ValuationResult:
    """Preserve the legacy index-swap valuation contract."""
    delta_exposure = base_value * parameters.delta_equivalent
    pnl = money(delta_exposure * underlying_return_shock)
    stressed_value = money(base_value + pnl)
    return ValuationResult(
        stressed_value,
        money(stressed_value - base_value),
        "derivative_delta_equivalent_mark_to_market",
        "Derivative P&L uses delta-equivalent current market value multiplied by the underlying return shock; notional is not used as market value.",
        {
            "formula_version": FORMULA_VERSION,
            "base_market_value_inr": str(base_value),
            "delta_equivalent": str(parameters.delta_equivalent),
            "delta_equivalent_exposure_inr": str(delta_exposure),
            "underlying_return_shock": str(underlying_return_shock),
            "notional_exposure_inr_not_used_as_value": str(parameters.notional_exposure_inr),
        },
    )


def calculate_position(
    *,
    asset_type: str,
    base_value: Decimal,
    parameters: Mapping[str, Any],
    shocks: Mapping[str, Decimal],
) -> ValuationResult:
    """Calculate one position using validated Milestone 5 parameters and scenario shocks."""
    if asset_type == "government_bond":
        yield_change = shocks.get("government_yield_change")
        if yield_change is None:
            raise ValueError("scenario does not provide a government yield shock")
        return government_bond_valuation(
            base_value,
            GovernmentBondParameters.model_validate(parameters),
            yield_change,
        )
    if asset_type == "corporate_bond":
        return corporate_bond_valuation(
            base_value,
            CorporateBondParameters.model_validate(parameters),
            shocks.get("corporate_benchmark_yield_change", Decimal("0")),
            shocks.get("corporate_spread_widening", Decimal("0")),
        )
    if asset_type == "corporate_loan":
        multiplier = shocks.get("corporate_loan_pd_multiplier")
        if multiplier is None:
            raise ValueError("scenario does not provide a corporate-loan PD multiplier")
        return corporate_loan_valuation(
            base_value,
            CorporateLoanParameters.model_validate(parameters),
            multiplier,
        )
    if asset_type == "equity":
        return equity_valuation(
            base_value,
            EquityParameters.model_validate(parameters),
            shocks.get("equity_return_shock", Decimal("0")),
        )
    if asset_type == "derivative":
        derivative_parameters = DerivativeParameters.model_validate(parameters)
        kind = (derivative_parameters.derivative_kind or derivative_parameters.instrument_type).casefold()
        if kind in {"interest_rate_swap", "irs"}:
            rate_shock = shocks.get(
                "interest_rate_shock_bps",
                shocks.get("corporate_benchmark_yield_change", shocks.get("government_yield_change", Decimal("0"))),
            )
            return interest_rate_swap_valuation(base_value, derivative_parameters, rate_shock)
        if kind in {"fx_forward", "forward"}:
            return fx_forward_valuation(
                base_value,
                derivative_parameters,
                shocks.get("fx_return_shock", Decimal("0")),
            )
        return derivative_valuation(
            base_value,
            derivative_parameters,
            shocks.get("equity_return_shock", Decimal("0")),
        )
    raise ValueError(f"unsupported asset type: {asset_type}")
