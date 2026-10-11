from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.signals import RiskSignalRead


class ScenarioParameterRead(BaseModel):
    name: str
    value: Decimal
    unit: str
    interpretation: str


class StressScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_id: str
    database_id: int
    name: str
    description: str
    event_category: str
    supported_event_types: list[str]
    required_signal_fields: list[str]
    relevance_scope: str
    trigger_threshold: int
    version: str
    enabled: bool
    assumptions: str
    parameters: list[ScenarioParameterRead]


class StressRunRequest(BaseModel):
    portfolio_id: int | None = None
    scenario_id: str = Field(min_length=1, max_length=64)
    risk_signal_id: int | None = Field(default=None, ge=1)
    trigger_mode: Literal["manual", "automatic"] = "manual"
    fresh_run: bool = False


class SignalStressRunRequest(BaseModel):
    portfolio_id: int | None = None
    scenario_id: str | None = Field(default=None, min_length=1, max_length=64)
    fresh_run: bool = False


class StressEligibilityRead(BaseModel):
    signal_id: int
    eligible: bool
    impact_score: int
    impact_threshold: int
    matching_scenarios: list[str]
    reasons: list[str]
    relevance_assessment: str


class StressPositionResultRead(BaseModel):
    result_id: int
    position_id: int
    position_key: str | None
    position_name: str | None
    asset_type: str | None
    position_value_before: Decimal
    position_value_after: Decimal
    contribution: Decimal
    inclusion_status: str
    calculation_method: str | None
    explanation: str | None
    applied_shocks: dict[str, Any]
    calculation_details: dict[str, Any]


class ReconciliationRead(BaseModel):
    position_pnl_sum: Decimal
    reported_pnl: Decimal
    difference: Decimal
    tolerance: Decimal
    reconciled: bool


class StressRunSummary(BaseModel):
    simulation_id: int
    run_id: int
    portfolio_id: int | None
    scenario_id: str
    scenario_name: str
    scenario_version: str
    trigger_signal_id: int | None
    triggered_by_signal_id: int | None
    trigger_mode: str
    status: str
    portfolio_value_before: Decimal
    portfolio_value_after: Decimal
    pnl: Decimal
    loss_percentage: Decimal
    portfolio_return_percentage: Decimal
    created_at: datetime


class StressRunDetail(StressRunSummary):
    model_version: str
    scenario_parameters: dict[str, Any]
    input_snapshot: dict[str, Any]
    data_provenance: dict[str, Any]
    validation_warnings: list[str]
    reconciliation: ReconciliationRead
    trigger_signal: RiskSignalRead | None = None
    results: list[StressPositionResultRead]


class StressRunPage(BaseModel):
    items: list[StressRunSummary]
    total: int = Field(ge=0)
    limit: int
    offset: int
