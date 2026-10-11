"""Record the signal that automatically triggered a stress-test run."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_triggered_by_signal"
down_revision: Union[str, Sequence[str], None] = "0006_stress_testing_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stress_test_runs",
        sa.Column("triggered_by_signal_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_stress_test_runs_triggered_by_signal_id",
        "stress_test_runs",
        "risk_signals",
        ["triggered_by_signal_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_stress_test_runs_triggered_by_signal_id",
        "stress_test_runs",
        ["triggered_by_signal_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_stress_test_runs_triggered_by_signal_id", table_name="stress_test_runs")
    op.drop_constraint(
        "fk_stress_test_runs_triggered_by_signal_id",
        "stress_test_runs",
        type_="foreignkey",
    )
    op.drop_column("stress_test_runs", "triggered_by_signal_id")
