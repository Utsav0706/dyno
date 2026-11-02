"""Labels table: human verdicts for judge calibration.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("scorer", sa.String(50), nullable=False),
        sa.Column("item", sa.Text(), nullable=False),
        sa.Column("label", sa.Boolean(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["result_id"], ["results.id"], name="fk_labels_result_id_results", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_labels"),
        sa.UniqueConstraint("result_id", "scorer", "item", name="uq_labels_result_id"),
    )


def downgrade() -> None:
    op.drop_table("labels")
