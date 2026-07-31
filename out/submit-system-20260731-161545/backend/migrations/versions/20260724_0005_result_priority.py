"""Add mutable result priority while preserving arrival sequence."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260724_0005"
down_revision = "20260724_0004"
branch_labels = None
depends_on = None

results = sa.table(
    "result_candidates",
    sa.column("arrival_seq", sa.Integer()),
    sa.column("priority", sa.Integer()),
)


def upgrade() -> None:
    op.add_column("result_candidates", sa.Column("priority", sa.Integer(), nullable=True))
    op.get_bind().execute(results.update().values(priority=results.c.arrival_seq))
    op.alter_column(
        "result_candidates",
        "priority",
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_query_priority",
        "result_candidates",
        ["query_id", "priority"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_query_priority", "result_candidates", type_="unique")
    op.drop_column("result_candidates", "priority")
