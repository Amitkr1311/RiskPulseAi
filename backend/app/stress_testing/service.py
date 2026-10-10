from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import Settings
from app.db.models import Article, ArticleEntity, Portfolio, PortfolioPosition, RiskSignal, StressScenario, StressTestResult, StressTestRun
from app.nlp.events import event_group_for_type
from app.schemas.portfolio import validate_position_parameters
from app.schemas.signals import EntitySignalRead, RiskSignalRead
from app.schemas.stress_testing import (
    ReconciliationRead,
    ScenarioParameterRead,
    StressEligibilityRead,
    StressPositionResultRead,
    StressRunDetail,
    StressRunPage,
    StressRunSummary,
    StressScenarioRead,
)
from app.stress_testing.calculations import calculate_position, money
from app.stress_testing.eligibility import StressEligibilityService, scenario_metadata, scenario_shocks
from app.stress_testing.errors import (
    StressIneligibleSignalError,
    StressPortfolioNotFoundError,
    StressRunNotFoundError,
    StressScenarioNotFoundError,
    StressSignalNotFoundError,
    StressValidationError,
)

PERCENT_QUANTUM = Decimal("0.0001")


class StressTestingService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.eligibility = StressEligibilityService(settings)

    def scenarios(self) -> list[StressScenarioRead]:
        scenarios = self.db.scalars(select(StressScenario).order_by(StressScenario.id.asc())).all()
        return [self.scenario_read(scenario) for scenario in scenarios if self._enabled(scenario)]

    def eligibility_for_signal(self, signal_id: int, portfolio_id: int | None = None) -> StressEligibilityRead:
        signal = self._get_signal(signal_id)
        portfolio = self._get_portfolio(portfolio_id)
        scenarios = self.db.scalars(select(StressScenario).order_by(StressScenario.id.asc())).all()
        result = self.eligibility.evaluate(signal, scenarios, self._positions(portfolio.id))
        return StressEligibilityRead(
            signal_id=signal.id,
            eligible=result.eligible,
            impact_score=result.impact_score,
            impact_threshold=result.impact_threshold,
            matching_scenarios=list(result.matching_scenarios),
            reasons=list(result.reasons),
            relevance_assessment=result.relevance_assessment,
        )

    def run(
        self,
        *,
        portfolio_id: int | None,
        scenario_id: str,
        risk_signal_id: int | None,
        trigger_mode: str,
        fresh_run: bool,
    ) -> tuple[StressRunDetail, bool]:
        portfolio = self._get_portfolio(portfolio_id)
        scenario = self._get_scenario(scenario_id)
        signal = self._get_signal(risk_signal_id) if risk_signal_id is not None else None
        positions = self._positions(portfolio.id)

        if signal is not None:
            all_scenarios = self.db.scalars(select(StressScenario).order_by(StressScenario.id.asc())).all()
            eligibility = self.eligibility.evaluate(signal, all_scenarios, positions)
            if not eligibility.eligible:
                raise StressIneligibleSignalError(list(eligibility.reasons))
            if scenario.scenario_key not in eligibility.matching_scenarios:
                raise StressIneligibleSignalError(["scenario_not_mapped_to_signal"])
        elif not self.eligibility.is_broad(scenario):
            raise StressValidationError("A targeted scenario requires a linked risk signal")

        base_key = (
            f"signal:{risk_signal_id}:{portfolio.id}:{scenario.scenario_key}:{scenario.version}"
            if risk_signal_id is not None
            else f"manual:{portfolio.id}:{scenario.scenario_key}:{scenario.version}"
        )
        trigger_key = f"{base_key}:fresh:{uuid.uuid4()}" if fresh_run else base_key
        if not fresh_run:
            existing = self.db.scalar(select(StressTestRun).where(StressTestRun.trigger_key == trigger_key))
            if existing is not None:
                return self.detail(existing.id), True

        shocks = scenario_shocks(scenario)
        calculations: list[dict[str, Any]] = []
        warnings: list[str] = []
        for position in positions:
            relevance = (
                self.eligibility.position_relevance(signal, position, scenario)
                if signal is not None
                else self.eligibility.manual_position_relevance(position, scenario)
            )
            if not relevance.included:
                calculations.append(self._excluded_calculation(position, relevance.reason, shocks))
                continue
            try:
                validate_position_parameters(position.asset_type, position.valuation_parameters)
                valuation = calculate_position(
                    asset_type=position.asset_type,
                    base_value=Decimal(position.market_value),
                    parameters=position.valuation_parameters,
                    shocks=shocks,
                )
                calculations.append(
                    self._included_calculation(position, valuation, relevance.reason, relevance.matched_terms, shocks)
                )
            except (ValueError, TypeError) as exc:
                reason = f"unsupported_valuation:{str(exc)}"
                warnings.append(f"{position.position_key}: {reason}")
                calculations.append(self._excluded_calculation(position, reason, shocks))

        base_total = money(sum((item["position_value_before"] for item in calculations), Decimal("0")))
        pnl = money(sum((item["contribution"] for item in calculations), Decimal("0")))
        stressed_total = money(base_total + pnl)
        loss_percentage = self._percentage(-pnl, base_total)
        return_percentage = self._percentage(pnl, base_total)
        status = "partial" if any(item["inclusion_status"] != "included" for item in calculations) else "completed"
        if not positions:
            status = "completed"

        run = StressTestRun(
            trigger_key=trigger_key,
            portfolio_id=portfolio.id,
            trigger_signal_id=signal.id if signal is not None else None,
            scenario_id=scenario.id,
            portfolio_value_before=base_total,
            portfolio_value_after=stressed_total,
            pnl=pnl,
            loss_percentage=loss_percentage,
            portfolio_return_percentage=return_percentage,
            status=status,
            trigger_mode=trigger_mode,
            scenario_version=scenario.version,
            model_version=self.settings.stress_model_version,
            scenario_parameters=scenario.shock_parameters,
            input_snapshot=self._input_snapshot(portfolio, positions, signal),
            data_provenance={
                "portfolio_is_demo": portfolio.is_demo,
                "signal_is_demo": signal.article.is_demo if signal is not None else None,
                "source": signal.article.source if signal is not None else "manual",
                "captured_at": datetime.now(UTC).isoformat(),
            },
            validation_warnings=warnings,
            reconciliation_tolerance=self.settings.stress_reconciliation_tolerance,
        )
        self.db.add(run)
        self.db.flush()
        for item in calculations:
            self.db.add(
                StressTestResult(
                    run_id=run.id,
                    position_id=item["position_id"],
                    position_value_before=item["position_value_before"],
                    position_value_after=item["position_value_after"],
                    contribution=item["contribution"],
                    position_key_snapshot=item["position_key"],
                    position_name_snapshot=item["position_name"],
                    asset_type_snapshot=item["asset_type"],
                    inclusion_status=item["inclusion_status"],
                    calculation_method=item["calculation_method"],
                    explanation=item["explanation"],
                    calculation_details=item["calculation_details"],
                )
            )
        self.db.commit()
        return self.detail(run.id), False

    def list_runs(
        self,
        *,
        portfolio_id: int | None,
        scenario_id: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> StressRunPage:
        filters = []
        if portfolio_id is not None:
            filters.append(StressTestRun.portfolio_id == portfolio_id)
        if scenario_id:
            scenario = self._get_scenario(scenario_id)
            filters.append(StressTestRun.scenario_id == scenario.id)
        if status:
            filters.append(StressTestRun.status == status)
        total = int(self.db.scalar(select(func.count()).select_from(StressTestRun).where(*filters)) or 0)
        runs = self.db.scalars(
            select(StressTestRun)
            .options(joinedload(StressTestRun.scenario))
            .where(*filters)
            .order_by(StressTestRun.created_at.desc(), StressTestRun.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return StressRunPage(items=[self.summary(run) for run in runs], total=total, limit=limit, offset=offset)

    def detail(self, run_id: int) -> StressRunDetail:
        run = self.db.scalar(
            select(StressTestRun)
            .options(
                joinedload(StressTestRun.scenario),
                joinedload(StressTestRun.trigger_signal).joinedload(RiskSignal.article).selectinload(Article.entities).joinedload(ArticleEntity.entity),
                selectinload(StressTestRun.results),
            )
            .where(StressTestRun.id == run_id)
        )
        if run is None:
            raise StressRunNotFoundError("Simulation run not found")
        results = sorted(run.results, key=lambda item: item.position_id)
        position_pnl_sum = money(sum((Decimal(item.contribution) for item in results), Decimal("0")))
        difference = money(position_pnl_sum - Decimal(run.pnl))
        return StressRunDetail(
            **self.summary(run).model_dump(),
            model_version=run.model_version,
            scenario_parameters=run.scenario_parameters or {},
            input_snapshot=run.input_snapshot or {},
            data_provenance=run.data_provenance or {},
            validation_warnings=run.validation_warnings or [],
            reconciliation=ReconciliationRead(
                position_pnl_sum=position_pnl_sum,
                reported_pnl=run.pnl,
                difference=difference,
                tolerance=run.reconciliation_tolerance,
                reconciled=abs(difference) <= run.reconciliation_tolerance,
            ),
            trigger_signal=self._signal_read(run.trigger_signal) if run.trigger_signal is not None else None,
            results=[
                StressPositionResultRead(
                    result_id=item.id,
                    position_id=item.position_id,
                    position_key=item.position_key_snapshot,
                    position_name=item.position_name_snapshot,
                    asset_type=item.asset_type_snapshot,
                    position_value_before=item.position_value_before,
                    position_value_after=item.position_value_after,
                    contribution=item.contribution,
                    inclusion_status=item.inclusion_status,
                    calculation_method=item.calculation_method,
                    explanation=item.explanation,
                    applied_shocks=(item.calculation_details or {}).get("applied_shocks", {}),
                    calculation_details=item.calculation_details or {},
                )
                for item in results
            ],
        )

    def scenarios_for_event(self, event_type: str) -> list[StressScenario]:
        return [
            scenario
            for scenario in self.db.scalars(select(StressScenario).order_by(StressScenario.id.asc())).all()
            if event_type in scenario_metadata(scenario).get("supported_event_types", [scenario.event_category])
        ]

    def scenario_read(self, scenario: StressScenario) -> StressScenarioRead:
        metadata = scenario_metadata(scenario)
        parameters = [ScenarioParameterRead.model_validate(parameter) for parameter in metadata.get("parameters", [])]
        return StressScenarioRead(
            scenario_id=scenario.scenario_key or str(scenario.id),
            database_id=scenario.id,
            name=scenario.name,
            description=scenario.assumptions,
            event_category=scenario.event_category,
            supported_event_types=[str(value) for value in metadata.get("supported_event_types", [scenario.event_category])],
            required_signal_fields=[str(value) for value in metadata.get("required_signal_fields", [])],
            relevance_scope=str(metadata.get("relevance_scope", "broad_market")),
            trigger_threshold=scenario.trigger_threshold,
            version=scenario.version,
            enabled=bool(metadata.get("enabled", True)),
            assumptions=scenario.assumptions,
            parameters=parameters,
        )

    def summary(self, run: StressTestRun) -> StressRunSummary:
        return StressRunSummary(
            simulation_id=run.id,
            run_id=run.id,
            portfolio_id=run.portfolio_id,
            scenario_id=run.scenario.scenario_key or str(run.scenario.id),
            scenario_name=run.scenario.name,
            scenario_version=run.scenario_version,
            trigger_signal_id=run.trigger_signal_id,
            trigger_mode=run.trigger_mode,
            status=run.status,
            portfolio_value_before=run.portfolio_value_before,
            portfolio_value_after=run.portfolio_value_after,
            pnl=run.pnl,
            loss_percentage=run.loss_percentage,
            portfolio_return_percentage=run.portfolio_return_percentage,
            created_at=run.created_at,
        )

    def _get_portfolio(self, portfolio_id: int | None) -> Portfolio:
        portfolio = (
            self.db.get(Portfolio, portfolio_id)
            if portfolio_id is not None
            else self.db.scalar(select(Portfolio).where(Portfolio.portfolio_key == "demo-banking-portfolio"))
        )
        if portfolio is None:
            raise StressPortfolioNotFoundError("Portfolio not found")
        return portfolio

    def _get_scenario(self, scenario_id: str) -> StressScenario:
        numeric_id = int(scenario_id) if scenario_id.isdigit() else -1
        scenario = self.db.scalar(
            select(StressScenario).where(
                or_(StressScenario.scenario_key == scenario_id, StressScenario.id == numeric_id)
            )
        )
        if scenario is None or not self._enabled(scenario):
            raise StressScenarioNotFoundError("Stress scenario not found or disabled")
        return scenario

    def _get_signal(self, signal_id: int | None) -> RiskSignal:
        if signal_id is None:
            raise StressSignalNotFoundError("Risk signal not found")
        signal = self.db.scalar(
            select(RiskSignal)
            .options(joinedload(RiskSignal.article).selectinload(Article.entities).joinedload(ArticleEntity.entity))
            .where(RiskSignal.id == signal_id)
        )
        if signal is None:
            raise StressSignalNotFoundError("Risk signal not found")
        return signal

    def _positions(self, portfolio_id: int) -> list[PortfolioPosition]:
        return self.db.scalars(
            select(PortfolioPosition).where(PortfolioPosition.portfolio_id == portfolio_id).order_by(PortfolioPosition.id.asc())
        ).all()

    @staticmethod
    def _enabled(scenario: StressScenario) -> bool:
        return bool(scenario_metadata(scenario).get("enabled", True))

    @staticmethod
    def _percentage(numerator: Decimal, denominator: Decimal) -> Decimal:
        if denominator == 0:
            return Decimal("0")
        return (numerator * Decimal("100") / denominator).quantize(PERCENT_QUANTUM, rounding=ROUND_HALF_UP)

    @staticmethod
    def _excluded_calculation(position: PortfolioPosition, reason: str, shocks: dict[str, Decimal]) -> dict[str, Any]:
        base = money(Decimal(position.market_value))
        return {
            "position_id": position.id,
            "position_key": position.position_key,
            "position_name": position.name,
            "asset_type": position.asset_type,
            "position_value_before": base,
            "position_value_after": base,
            "contribution": Decimal("0.00"),
            "inclusion_status": "excluded",
            "calculation_method": None,
            "explanation": f"Position retained at base value because it was excluded: {reason}.",
            "calculation_details": {"formula_version": "stress-formulas-v1", "exclusion_reason": reason, "applied_shocks": {key: str(value) for key, value in shocks.items()}},
        }

    @staticmethod
    def _included_calculation(position: PortfolioPosition, valuation: Any, relevance: str, matched_terms: tuple[str, ...], shocks: dict[str, Decimal]) -> dict[str, Any]:
        return {
            "position_id": position.id,
            "position_key": position.position_key,
            "position_name": position.name,
            "asset_type": position.asset_type,
            "position_value_before": money(Decimal(position.market_value)),
            "position_value_after": valuation.stressed_value,
            "contribution": valuation.pnl,
            "inclusion_status": "included",
            "calculation_method": valuation.calculation_method,
            "explanation": f"Included by {relevance}" + (f" ({', '.join(matched_terms)})." if matched_terms else "."),
            "calculation_details": {**valuation.details, "relevance_reason": relevance, "matched_terms": list(matched_terms), "applied_shocks": {key: str(value) for key, value in shocks.items()}},
        }

    @staticmethod
    def _input_snapshot(portfolio: Portfolio, positions: list[PortfolioPosition], signal: RiskSignal | None) -> dict[str, Any]:
        return {
            "portfolio": {"id": portfolio.id, "portfolio_key": portfolio.portfolio_key, "name": portfolio.name, "currency": portfolio.currency},
            "positions": [
                {"id": position.id, "position_key": position.position_key, "name": position.name, "asset_type": position.asset_type, "market_value": str(position.market_value), "currency": position.currency, "sector": position.sector, "borrower": position.borrower, "valuation_parameters": position.valuation_parameters}
                for position in positions
            ],
            "risk_signal": {
                "id": signal.id,
                "article_id": signal.article_id,
                "event_type": signal.event_type,
                "impact_score": signal.impact_score,
                "entity_name": signal.entity_name,
                "explanation": signal.explanation,
            } if signal is not None else None,
        }

    @staticmethod
    def _signal_read(signal: RiskSignal) -> RiskSignalRead:
        raw_entities = signal.entities
        if raw_entities is None:
            raw_entities = [
                {"mention": relation.raw_mention, "canonical_name": relation.entity.canonical_name, "identifier": relation.entity.identifier, "resolved": relation.entity.identifier is not None, "entity_type": relation.entity.entity_type}
                for relation in signal.article.entities
            ]
        return RiskSignalRead(
            id=signal.id,
            article_id=signal.article_id,
            source=signal.article.source,
            article_title=signal.article.title,
            article_url=signal.article.url,
            is_demo=signal.article.is_demo,
            article=signal.article,
            entities=[EntitySignalRead.model_validate(entity) for entity in raw_entities],
            sentiment_label=signal.sentiment_label,
            sentiment_score=float(signal.sentiment_score),
            sentiment_probabilities={key: float(value) for key, value in signal.sentiment_probabilities.items()} if signal.sentiment_probabilities else None,
            event_type=signal.event_type,
            event_group=event_group_for_type(signal.event_type),
            event_confidence=float(signal.event_confidence) if signal.event_confidence is not None else None,
            impact_score=signal.impact_score,
            impact_factors=signal.impact_factors,
            explanation=signal.explanation,
            model_version=signal.model_version,
            model_metadata=signal.model_metadata,
            scoring_config_version=signal.scoring_config_version,
            created_at=signal.created_at,
        )
