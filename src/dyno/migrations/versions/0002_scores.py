"""Scores table; scorer specs on runs; match/check on cases.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable, no server default: older rows get NULL, which the code reads as
    # "default scorers" / "suite's match mode".
    # Plain ADD COLUMN, not batch mode: on SQLite batch mode can copy and drop the table,
    # and with foreign keys on, dropping `cases` would cascade-delete its results.
    op.add_column("runs", sa.Column("scorers", sa.JSON(), nullable=True))
    op.add_column("cases", sa.Column("match_mode", sa.String(10), nullable=True))
    op.add_column("cases", sa.Column("check_fn", sa.String(200), nullable=True))

    op.create_table(
        "scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("scorer", sa.String(50), nullable=False),
        sa.Column("score", sa.Double(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["result_id"], ["results.id"], name="fk_scores_result_id_results", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scores"),
        sa.UniqueConstraint("result_id", "scorer", name="uq_scores_result_id"),
    )


def downgrade() -> None:
    op.drop_table("scores")
    # Native DROP COLUMN (SQLite 3.35+), for the same reason as above.
    op.drop_column("cases", "check_fn")
    op.drop_column("cases", "match_mode")
    op.drop_column("runs", "scorers")
