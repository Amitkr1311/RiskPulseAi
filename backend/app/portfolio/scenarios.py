from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class ShockParameter(BaseModel):
    name: str
    value: Decimal
    unit: Literal["decimal_return", "absolute_rate_change", "basis_points", "multiplier", "decimal_rate"]
    interpretation: str


class ScenarioTemplate(BaseModel):
    scenario_key: str
    name: str
    event_category: Literal["geopolitical", "macroeconomic", "credit_event", "regulatory", "market_crash"]
    supported_event_types: list[str]
    required_signal_fields: list[str]
    relevance_scope: Literal["broad_market", "entity_or_sector", "entity_or_sector_or_broad"]
    trigger_threshold: int = Field(ge=1, le=10)
    version: str
    assumptions: str
    shock_parameters: list[ShockParameter]


SCENARIO_TEMPLATES = [
    ScenarioTemplate(
        scenario_key="geopolitical_shock",
        name="Geopolitical shock",
        event_category="geopolitical",
        supported_event_types=["geopolitical"],
        required_signal_fields=["impact_score", "event_type"],
        relevance_scope="broad_market",
        trigger_threshold=7,
        version="1.0",
        assumptions="Hypothetical educational shock. The flight-to-quality government-bond assumption is illustrative, not a forecast.",
        shock_parameters=[
            ShockParameter(name="equity_return_shock", value=Decimal("-0.10"), unit="decimal_return", interpretation="Relevant equity positions lose 10% of market value."),
            ShockParameter(name="corporate_spread_widening", value=Decimal("150"), unit="basis_points", interpretation="Corporate credit spreads widen by 150 basis points."),
            ShockParameter(name="government_yield_change", value=Decimal("-25"), unit="basis_points", interpretation="Government yields fall by 25 basis points in an illustrative flight to quality."),
            ShockParameter(name="corporate_loan_pd_multiplier", value=Decimal("1.5"), unit="multiplier", interpretation="Corporate-loan baseline PD is multiplied by 1.5 and capped at 100%."),
        ],
    ),
    ScenarioTemplate(
        scenario_key="macroeconomic_rate_shock",
        name="Macroeconomic and interest-rate shock",
        event_category="macroeconomic",
        supported_event_types=["macroeconomic"],
        required_signal_fields=["impact_score", "event_type"],
        relevance_scope="broad_market",
        trigger_threshold=7,
        version="1.0",
        assumptions="Hypothetical educational rate shock. Benchmark-rate and credit-spread effects are modeled separately.",
        shock_parameters=[
            ShockParameter(name="government_yield_change", value=Decimal("200"), unit="basis_points", interpretation="Government yields rise by 200 basis points."),
            ShockParameter(name="corporate_benchmark_yield_change", value=Decimal("200"), unit="basis_points", interpretation="Corporate benchmark yields rise by 200 basis points."),
            ShockParameter(name="corporate_spread_widening", value=Decimal("75"), unit="basis_points", interpretation="Corporate credit spreads widen by 75 basis points."),
            ShockParameter(name="equity_return_shock", value=Decimal("-0.08"), unit="decimal_return", interpretation="Relevant equity positions lose 8% of market value."),
            ShockParameter(name="corporate_loan_pd_multiplier", value=Decimal("1.25"), unit="multiplier", interpretation="Corporate-loan baseline PD is multiplied by 1.25 and capped at 100%."),
        ],
    ),
    ScenarioTemplate(
        scenario_key="credit_deterioration",
        name="Credit deterioration",
        event_category="credit_event",
        supported_event_types=["credit_event"],
        required_signal_fields=["impact_score", "event_type", "entity_or_sector"],
        relevance_scope="entity_or_sector",
        trigger_threshold=7,
        version="1.0",
        assumptions="Hypothetical targeted credit shock. Incremental expected credit loss is reported separately from principal exposure.",
        shock_parameters=[
            ShockParameter(name="corporate_loan_pd_multiplier", value=Decimal("2.0"), unit="multiplier", interpretation="Relevant loan baseline PD is doubled and capped at 100%."),
            ShockParameter(name="corporate_spread_widening", value=Decimal("250"), unit="basis_points", interpretation="Relevant corporate credit spreads widen by 250 basis points."),
            ShockParameter(name="equity_return_shock", value=Decimal("-0.05"), unit="decimal_return", interpretation="Relevant equity positions lose 5% of market value."),
        ],
    ),
    ScenarioTemplate(
        scenario_key="regulatory_shock",
        name="Regulatory or sector-specific shock",
        event_category="regulatory",
        supported_event_types=["regulatory"],
        required_signal_fields=["impact_score", "event_type", "entity_or_sector"],
        relevance_scope="entity_or_sector",
        trigger_threshold=7,
        version="1.0",
        assumptions="Hypothetical targeted regulatory shock. A position is included only when an entity or sector relationship is supported.",
        shock_parameters=[
            ShockParameter(name="equity_return_shock", value=Decimal("-0.12"), unit="decimal_return", interpretation="Relevant sector equity positions lose 12% of market value."),
            ShockParameter(name="corporate_spread_widening", value=Decimal("100"), unit="basis_points", interpretation="Relevant corporate credit spreads widen by 100 basis points."),
            ShockParameter(name="corporate_loan_pd_multiplier", value=Decimal("1.5"), unit="multiplier", interpretation="Relevant loan baseline PD is multiplied by 1.5 and capped at 100%."),
        ],
    ),
    ScenarioTemplate(
        scenario_key="broad_market_crash",
        name="Broad market crash",
        event_category="market_crash",
        supported_event_types=["market_crash"],
        required_signal_fields=["impact_score", "event_type"],
        relevance_scope="broad_market",
        trigger_threshold=7,
        version="1.0",
        assumptions="Hypothetical educational broad-market shock, not a calibrated stress scenario or market forecast. Government yields fall by 50 basis points as an explicit flight-to-quality assumption.",
        shock_parameters=[
            ShockParameter(name="equity_return_shock", value=Decimal("-0.20"), unit="decimal_return", interpretation="Equity positions lose 20% of market value."),
            ShockParameter(name="corporate_spread_widening", value=Decimal("200"), unit="basis_points", interpretation="Corporate credit spreads widen by 200 basis points."),
            ShockParameter(name="corporate_loan_pd_multiplier", value=Decimal("1.5"), unit="multiplier", interpretation="Corporate-loan baseline PD is multiplied by 1.5 and capped at 100%."),
            ShockParameter(name="government_yield_change", value=Decimal("-50"), unit="basis_points", interpretation="Government yields fall by 50 basis points under the documented illustrative assumption."),
        ],
    ),
]


def scenario_records() -> list[dict[str, object]]:
    return [
        {
            "scenario_key": template.scenario_key,
            "name": template.name,
            "event_category": template.event_category,
            "trigger_threshold": template.trigger_threshold,
            "version": template.version,
            "assumptions": template.assumptions,
            "shock_parameters": {
                "parameters": [parameter.model_dump(mode="json") for parameter in template.shock_parameters],
                "supported_event_types": template.supported_event_types,
                "required_signal_fields": template.required_signal_fields,
                "relevance_scope": template.relevance_scope,
                "enabled": True,
            },
        }
        for template in SCENARIO_TEMPLATES
    ]
