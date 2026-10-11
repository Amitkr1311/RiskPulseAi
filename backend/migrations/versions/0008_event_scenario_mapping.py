"""Persist the complete event-to-scenario mapping and geopolitical shocks."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_event_scenario_mapping"
down_revision: Union[str, Sequence[str], None] = "0007_triggered_by_signal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EVENT_SCENARIO_MAP = {
    "geopolitical_shock": ["geopolitical"],
    "macroeconomic_rate_shock": ["macroeconomic", "sovereign_risk", "currency_shock"],
    "credit_deterioration": ["credit_event", "liquidity_stress", "fraud_misconduct"],
    "regulatory_shock": [
        "merger_acquisition",
        "earnings",
        "regulatory",
        "product_launch",
        "company_performance",
        "cyber_incident",
        "litigation",
        "operational_disruption",
        "climate_risk",
    ],
    "broad_market_crash": ["market_crash", "other"],
}


def upgrade() -> None:
    table = sa.table(
        "stress_scenarios",
        sa.column("scenario_key", sa.String(length=64)),
        sa.column("shock_parameters", sa.JSON()),
    )
    bind = op.get_bind()
    rows = bind.execute(sa.select(table.c.scenario_key, table.c.shock_parameters)).all()
    for scenario_key, raw_parameters in rows:
        supported_event_types = EVENT_SCENARIO_MAP.get(scenario_key)
        if supported_event_types is None:
            continue
        parameters = dict(raw_parameters or {})
        parameters["supported_event_types"] = supported_event_types
        if scenario_key == "geopolitical_shock":
            shocks = list(parameters.get("parameters", []))
            existing_names = {item.get("name") for item in shocks if isinstance(item, dict)}
            if "fx_return_shock" not in existing_names:
                shocks.append(
                    {
                        "name": "fx_return_shock",
                        "value": "-0.05",
                        "unit": "decimal_return",
                        "interpretation": "Relevant FX exposures lose 5% from the adverse currency move.",
                    }
                )
            if "oil_price_shock" not in existing_names:
                shocks.append(
                    {
                        "name": "oil_price_shock",
                        "value": "0.20",
                        "unit": "decimal_return",
                        "interpretation": "Oil prices rise by 20% as an illustrative commodity shock.",
                    }
                )
            parameters["parameters"] = shocks
        bind.execute(
            table.update()
            .where(table.c.scenario_key == scenario_key)
            .values(shock_parameters=parameters)
        )


def downgrade() -> None:
    table = sa.table(
        "stress_scenarios",
        sa.column("scenario_key", sa.String(length=64)),
        sa.column("shock_parameters", sa.JSON()),
    )
    bind = op.get_bind()
    for scenario_key, event_types in EVENT_SCENARIO_MAP.items():
        raw_parameters = bind.execute(
            sa.select(table.c.shock_parameters).where(table.c.scenario_key == scenario_key)
        ).scalar_one_or_none()
        if raw_parameters is None:
            continue
        parameters = dict(raw_parameters)
        parameters["supported_event_types"] = [event_types[0]]
        if scenario_key == "geopolitical_shock":
            parameters["parameters"] = [
                item
                for item in parameters.get("parameters", [])
                if isinstance(item, dict)
                and item.get("name") not in {"fx_return_shock", "oil_price_shock"}
            ]
        bind.execute(
            table.update()
            .where(table.c.scenario_key == scenario_key)
            .values(shock_parameters=parameters)
        )
