"""Keep active priorities contiguous within each query."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260727_0006"
down_revision = "20260724_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_query_priority", "result_candidates", type_="unique")
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY query_id
                        ORDER BY priority, arrival_seq
                    ) AS compact_priority
                FROM result_candidates
                WHERE deleted_at IS NULL
            )
            UPDATE candidates
            SET candidates.priority = ranked.compact_priority
            FROM result_candidates AS candidates
            INNER JOIN ranked ON ranked.id = candidates.id
            """
        )
    )
    op.create_index(
        "ux_active_query_priority",
        "result_candidates",
        ["query_id", "priority"],
        unique=True,
        mssql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_active_query_priority", table_name="result_candidates")
    op.execute(sa.text("UPDATE result_candidates SET priority = arrival_seq"))
    op.create_unique_constraint(
        "uq_query_priority",
        "result_candidates",
        ["query_id", "priority"],
    )
