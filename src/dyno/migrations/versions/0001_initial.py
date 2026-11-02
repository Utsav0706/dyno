"""Initial tables: runs, cases, results, steps.

Revision ID: 0001
Revises:
Create Date: 2026-11-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("suite", sa.String(200), nullable=False),
        sa.Column("agent", sa.String(200), nullable=False),
        sa.Column("k", sa.Integer(), nullable=False),
        sa.Column("git_commit", sa.String(40), nullable=True),
        sa.Column("git_dirty", sa.Boolean(), nullable=True),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("dyno_version", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_runs"),
    )
    op.create_index("ix_runs_config_hash", "runs", ["config_hash"])

    op.create_table(
        "cases",
        sa.Column("run_id", sa.String(32), nullable=False),
        sa.Column("case_id", sa.String(200), nullable=False),
        sa.Column("input", sa.Text(), nullable=False),
        sa.Column("expected", sa.JSON(), nullable=True),
        sa.Column("must_call", sa.JSON(), nullable=False),
        sa.Column("must_not_call", sa.JSON(), nullable=False),
        sa.Column("max_steps", sa.Integer(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"], name="fk_cases_run_id_runs", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("run_id", "case_id", name="pk_cases"),
    )

    op.create_table(
        "results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(32), nullable=False),
        sa.Column("case_id", sa.String(200), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("final_answer", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Double(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_gbp", sa.Double(), nullable=True),
        sa.Column("n_steps", sa.Integer(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"], name="fk_results_run_id_runs", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "case_id"],
            ["cases.run_id", "cases.case_id"],
            name="fk_results_run_id_cases",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_results"),
        sa.UniqueConstraint("run_id", "case_id", "attempt", name="uq_results_run_id"),
    )
    op.create_index("ix_results_run_id", "results", ["run_id"])

    op.create_table(
        "steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("args", sa.JSON(), nullable=False),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_gbp", sa.Double(), nullable=True),
        sa.Column("latency_ms", sa.Double(), nullable=True),
        sa.ForeignKeyConstraint(
            ["result_id"], ["results.id"], name="fk_steps_result_id_results", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_steps"),
        sa.UniqueConstraint("result_id", "idx", name="uq_steps_result_id"),
    )


def downgrade() -> None:
    op.drop_table("steps")
    op.drop_index("ix_results_run_id", table_name="results")
    op.drop_table("results")
    op.drop_table("cases")
    op.drop_index("ix_runs_config_hash", table_name="runs")
    op.drop_table("runs")
