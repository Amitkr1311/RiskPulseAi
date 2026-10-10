from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Any

from app.core.config import Settings
from app.db.models import PortfolioPosition, RiskSignal, StressScenario


def normalize_match(value: str | None) -> str:
    if not isinstance(value, str) or not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def scenario_shocks(scenario: StressScenario) -> dict[str, Decimal]:
    raw = scenario.shock_parameters or {}
    parameters = raw.get("parameters", []) if isinstance(raw, dict) else []
    return {
        str(parameter["name"]): Decimal(str(parameter["value"]))
        for parameter in parameters
        if isinstance(parameter, dict) and "name" in parameter and "value" in parameter
    }


def scenario_metadata(scenario: StressScenario) -> dict[str, Any]:
    raw = scenario.shock_parameters
    return raw if isinstance(raw, dict) else {}


@dataclass(frozen=True)
class PositionRelevance:
    included: bool
    reason: str
    matched_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reasons: tuple[str, ...]
    impact_threshold: int
    impact_score: int
    matching_scenarios: tuple[str, ...]
    relevance_assessment: str


class StressEligibilityService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(
        self,
        signal: RiskSignal,
        scenarios: list[StressScenario],
        positions: list[PortfolioPosition],
    ) -> EligibilityResult:
        reasons: list[str] = []
        if signal.impact_score <= self.settings.stress_impact_threshold:
            reasons.append("below_impact_threshold")

        matching = [
            scenario
            for scenario in scenarios
            if signal.event_type in set(self._supported_event_types(scenario))
            and scenario.trigger_threshold <= signal.impact_score
        ]
        if not matching:
            reasons.append("unsupported_event_type")

        relevance = "not_assessed"
        if matching:
            relevant_scenarios = [scenario for scenario in matching if self.is_broad(scenario)]
            if not relevant_scenarios:
                relevant_scenarios = [
                    scenario
                    for scenario in matching
                    if any(self.position_relevance(signal, position, scenario).included for position in positions)
                ]
                if not relevant_scenarios:
                    reasons.append("insufficient_portfolio_relevance")
                    relevance = "no_exact_entity_or_sector_match"
                else:
                    relevance = "entity_or_sector_match"
            else:
                relevance = "broad_market_scenario"

        return EligibilityResult(
            eligible=not reasons,
            reasons=tuple(dict.fromkeys(reasons)),
            impact_threshold=self.settings.stress_impact_threshold,
            impact_score=signal.impact_score,
            matching_scenarios=tuple(scenario.scenario_key or str(scenario.id) for scenario in matching),
            relevance_assessment=relevance,
        )

    def position_relevance(
        self,
        signal: RiskSignal,
        position: PortfolioPosition,
        scenario: StressScenario,
    ) -> PositionRelevance:
        if self.is_broad(scenario):
            return PositionRelevance(True, "broad_market_scenario")

        signal_terms = self.signal_terms(signal)
        position_terms = self.position_terms(position)
        matches = sorted(signal_terms.intersection(position_terms))
        if matches:
            return PositionRelevance(True, "exact_entity_or_instrument_match", tuple(matches))

        sector = normalize_match(position.sector)
        if sector and sector in signal_terms:
            return PositionRelevance(True, "exact_sector_match", (sector,))
        return PositionRelevance(False, "not_relevant_to_targeted_signal")

    def manual_position_relevance(self, position: PortfolioPosition, scenario: StressScenario) -> PositionRelevance:
        if self.is_broad(scenario):
            return PositionRelevance(True, "broad_market_scenario")
        return PositionRelevance(False, "targeted_scenario_requires_signal")

    @staticmethod
    def is_broad(scenario: StressScenario) -> bool:
        return scenario_metadata(scenario).get("relevance_scope") == "broad_market"

    @staticmethod
    def _supported_event_types(scenario: StressScenario) -> list[str]:
        values = scenario_metadata(scenario).get("supported_event_types", [scenario.event_category])
        return [str(value) for value in values]

    @staticmethod
    def signal_terms(signal: RiskSignal) -> set[str]:
        terms: set[str] = set()
        for value in (signal.entity_name,):
            normalized = normalize_match(value)
            if normalized:
                terms.add(normalized)
        for entity in signal.entities or []:
            if not isinstance(entity, dict):
                continue
            for field in ("canonical_name", "mention", "identifier"):
                normalized = normalize_match(entity.get(field) if isinstance(entity.get(field), str) else None)
                if normalized:
                    terms.add(normalized)
        return terms

    @staticmethod
    def position_terms(position: PortfolioPosition) -> set[str]:
        values: list[str | None] = [position.borrower, position.sector]
        parameters = position.valuation_parameters or {}
        for key in ("borrower_group_id", "issuer", "ticker", "instrument_name", "underlying", "sector"):
            value = parameters.get(key)
            values.append(str(value) if value is not None else None)
        return {normalized for value in values if (normalized := normalize_match(value))}
