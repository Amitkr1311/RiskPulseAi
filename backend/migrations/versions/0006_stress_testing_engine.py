"""Add auditable stress-testing runs, results, and versioned scenario keys."""

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_stress_testing_engine"
down_revision: Union[str, Sequence[str], None] = "0005_portfolio_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCENARIO_DATA = {
    "geopolitical": {
        "scenario_key": "geopolitical_shock",
        "name": "Geopolitical shock",
        "parameters": [
            {"name": "equity_return_shock", "value": "-0.10", "unit": "decimal_return", "interpretation": "Relevant equity positions lose 10% of market value."},
            {"name": "corporate_spread_widening", "value": "150", "unit": "basis_points", "interpretation": "Corporate credit spreads widen by 150 basis points."},
            {"name": "government_yield_change", "value": "-25", "unit": "basis_points", "interpretation": "Government yields fall by 25 basis points in an illustrative flight to quality."},
            {"name": "corporate_loan_pd_multiplier", "value": "1.5", "unit": "multiplier", "interpretation": "Corporate-loan baseline PD is multiplied by 1.5 and capped at 100%."},
        ],
        "supported_event_types": ["geopolitical"], "required_signal_fields": ["impact_score", "event_type"], "relevance_scope": "broad_market",
        "assumptions": "Hypothetical educational shock. The flight-to-quality government-bond assumption is illustrative, not a forecast.",
    },
    "macroeconomic": {
        "scenario_key": "macroeconomic_rate_shock",
        "name": "Macroeconomic and interest-rate shock",
        "parameters": [
            {"name": "government_yield_change", "value": "200", "unit": "basis_points", "interpretation": "Government yields rise by 200 basis points."},
            {"name": "corporate_benchmark_yield_change", "value": "200", "unit": "basis_points", "interpretation": "Corporate benchmark yields rise by 200 basis points."},
            {"name": "corporate_spread_widening", "value": "75", "unit": "basis_points", "interpretation": "Corporate credit spreads widen by 75 basis points."},
            {"name": "equity_return_shock", "value": "-0.08", "unit": "decimal_return", "interpretation": "Relevant equity positions lose 8% of market value."},
            {"name": "corporate_loan_pd_multiplier", "value": "1.25", "unit": "multiplier", "interpretation": "Corporate-loan baseline PD is multiplied by 1.25 and capped at 100%."},
        ],
        "supported_event_types": ["macroeconomic"], "required_signal_fields": ["impact_score", "event_type"], "relevance_scope": "broad_market",
        "assumptions": "Hypothetical educational rate shock. Benchmark-rate and credit-spread effects are modeled separately.",
    },
    "credit_event": {
        "scenario_key": "credit_deterioration",
        "name": "Credit deterioration",
        "parameters": [
            {"name": "corporate_loan_pd_multiplier", "value": "2.0", "unit": "multiplier", "interpretation": "Relevant loan baseline PD is doubled and capped at 100%."},
            {"name": "corporate_spread_widening", "value": "250", "unit": "basis_points", "interpretation": "Relevant corporate credit spreads widen by 250 basis points."},
            {"name": "equity_return_shock", "value": "-0.05", "unit": "decimal_return", "interpretation": "Relevant equity positions lose 5% of market value."},
        ],
        "supported_event_types": ["credit_event"], "required_signal_fields": ["impact_score", "event_type", "entity_or_sector"], "relevance_scope": "entity_or_sector",
        "assumptions": "Hypothetical targeted credit shock. Incremental expected credit loss is reported separately from principal exposure.",
    },
    "regulatory": {
        "scenario_key": "regulatory_shock",
        "name": "Regulatory or sector-specific shock",
        "parameters": [
            {"name": "equity_return_shock", "value": "-0.12", "unit": "decimal_return", "interpretation": "Relevant sector equity positions lose 12% of market value."},
            {"name": "corporate_spread_widening", "value": "100", "unit": "basis_points", "interpretation": "Relevant corporate credit spreads widen by 100 basis points."},
            {"name": "corporate_loan_pd_multiplier", "value": "1.5", "unit": "multiplier", "interpretation": "Relevant loan baseline PD is multiplied by 1.5 and capped at 100%."},
        ],
        "supported_event_types": ["regulatory"], "required_signal_fields": ["impact_score", "event_type", "entity_or_sector"], "relevance_scope": "entity_or_sector",
        "assumptions": "Hypothetical targeted regulatory shock. A position is included only when an entity or sector relationship is supported.",
    },
    "market_crash": {
        "scenario_key": "broad_market_crash",
        "name": "Broad market crash",
        "parameters": [
            {"name": "equity_return_shock", "value": "-0.20", "unit": "decimal_return", "interpretation": "Equity positions lose 20% of market value."},
            {"name": "corporate_spread_widening", "value": "200", "unit": "basis_points", "interpretation": "Corporate credit spreads widen by 200 basis points."},
            {"name": "corporate_loan_pd_multiplier", "value": "1.5", "unit": "multiplier", "interpretation": "Corporate-loan baseline PD is multiplied by 1.5 and capped at 100%."},
            {"name": "government_yield_change", "value": "-50", "unit": "basis_points", "interpretation": "Government yields fall by 50 basis points under the documented illustrative assumption."},
        ],
        "supported_event_types": ["market_crash"], "required_signal_fields": ["impact_score", "event_type"], "relevance_scope": "broad_market",
        "assumptions": "Hypothetical educational broad-market shock, not a calibrated stress scenario or market forecast. Government yields fall by 50 basis points as an explicit flight-to-quality assumption.",
    },
}


def upgrade() -> None:
    op.add_column("stress_scenarios", sa.Column("scenario_key", sa.String(length=64), nullable=True))
    op.add_column("stress_test_runs", sa.Column("portfolio_id", sa.Integer(), nullable=True))
    op.add_column("stress_test_runs", sa.Column("portfolio_return_percentage", sa.Numeric(8, 4), nullable=False, server_default="0"))
    op.add_column("stress_test_runs", sa.Column("trigger_mode", sa.String(length=32), nullable=False, server_default="manual"))
    op.add_column("stress_test_runs", sa.Column("scenario_version", sa.String(length=32), nullable=False, server_default="1.0"))
    op.add_column("stress_test_runs", sa.Column("model_version", sa.String(length=64), nullable=False, server_default="stress-v1"))
    op.add_column("stress_test_runs", sa.Column("scenario_parameters", sa.JSON(), nullable=True))
    op.add_column("stress_test_runs", sa.Column("input_snapshot", sa.JSON(), nullable=True))
    op.add_column("stress_test_runs", sa.Column("data_provenance", sa.JSON(), nullable=True))
    op.add_column("stress_test_runs", sa.Column("validation_warnings", sa.JSON(), nullable=True))
    op.add_column("stress_test_runs", sa.Column("reconciliation_tolerance", sa.Numeric(18, 2), nullable=False, server_default="0.01"))
    op.create_foreign_key("fk_stress_test_runs_portfolio_id", "stress_test_runs", "portfolios", ["portfolio_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_stress_test_runs_portfolio_id", "stress_test_runs", ["portfolio_id"])

    op.add_column("stress_test_results", sa.Column("position_key_snapshot", sa.String(length=64), nullable=True))
    op.add_column("stress_test_results", sa.Column("position_name_snapshot", sa.String(length=255), nullable=True))
    op.add_column("stress_test_results", sa.Column("asset_type_snapshot", sa.String(length=64), nullable=True))
    op.add_column("stress_test_results", sa.Column("inclusion_status", sa.String(length=32), nullable=False, server_default="included"))
    op.add_column("stress_test_results", sa.Column("calculation_method", sa.String(length=128), nullable=True))
    op.add_column("stress_test_results", sa.Column("explanation", sa.Text(), nullable=True))

    bind = op.get_bind()
    table = sa.table(
        "stress_scenarios",
        sa.column("id", sa.Integer),
        sa.column("event_category", sa.String),
        sa.column("scenario_key", sa.String),
        sa.column("name", sa.String),
        sa.column("trigger_threshold", sa.Integer),
        sa.column("version", sa.String),
        sa.column("assumptions", sa.Text),
        sa.column("shock_parameters", sa.JSON),
    )
    for event_category, data in SCENARIO_DATA.items():
        bind.execute(
            table.update().where(table.c.event_category == event_category).values(
                scenario_key=data["scenario_key"],
                name=data["name"],
                trigger_threshold=7,
                version="1.0",
                assumptions=data["assumptions"],
                shock_parameters=json.loads(json.dumps({"parameters": data["parameters"], "supported_event_types": data["supported_event_types"], "required_signal_fields": data["required_signal_fields"], "relevance_scope": data["relevance_scope"], "enabled": True})),
            )
        )
    op.create_unique_constraint("uq_stress_scenarios_scenario_key", "stress_scenarios", ["scenario_key"])


def downgrade() -> None:
    op.drop_constraint("uq_stress_scenarios_scenario_key", "stress_scenarios", type_="unique")
    op.drop_column("stress_scenarios", "scenario_key")
    op.drop_column("stress_test_results", "explanation")
    op.drop_column("stress_test_results", "calculation_method")
    op.drop_column("stress_test_results", "inclusion_status")
    op.drop_column("stress_test_results", "asset_type_snapshot")
    op.drop_column("stress_test_results", "position_name_snapshot")
    op.drop_column("stress_test_results", "position_key_snapshot")
    op.drop_index("ix_stress_test_runs_portfolio_id", table_name="stress_test_runs")
    op.drop_constraint("fk_stress_test_runs_portfolio_id", "stress_test_runs", type_="foreignkey")
    for column in ("reconciliation_tolerance", "validation_warnings", "data_provenance", "input_snapshot", "scenario_parameters", "model_version", "scenario_version", "trigger_mode", "portfolio_return_percentage", "portfolio_id"):
        op.drop_column("stress_test_runs", column)
