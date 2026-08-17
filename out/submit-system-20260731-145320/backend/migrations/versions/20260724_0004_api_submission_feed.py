"""Consolidate query rows into one global API submission feed."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "20260724_0004"
down_revision = "20260722_0003"
branch_labels = None
depends_on = None

API_QUERY_SET_ID = "00000000-0000-0000-0000-000000000001"

query_sets = sa.table(
    "query_sets",
    sa.column("id", sa.String(36)),
    sa.column("name", sa.Unicode(255)),
    sa.column("original_zip_name", sa.Unicode(255)),
    sa.column("is_active", sa.Boolean()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("created_by", sa.Unicode(255)),
    sa.column("import_status", sa.String(32)),
)
queries = sa.table(
    "queries",
    sa.column("id", sa.String(36)),
    sa.column("query_set_id", sa.String(36)),
    sa.column("file_name_key", sa.Unicode(255)),
    sa.column("display_order", sa.Integer()),
    sa.column("next_arrival_seq", sa.Integer()),
    sa.column("created_at", sa.DateTime(timezone=True)),
)
results = sa.table(
    "result_candidates",
    sa.column("id", sa.String(36)),
    sa.column("query_id", sa.String(36)),
    sa.column("arrival_seq", sa.Integer()),
    sa.column("created_at", sa.DateTime(timezone=True)),
)


def _timestamp(value: Any) -> float:
    if not isinstance(value, datetime):
        return float("inf")
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return aware.timestamp()


def upgrade() -> None:
    bind = op.get_bind()
    active_set_ids = {
        str(row.id)
        for row in bind.execute(
            sa.select(query_sets.c.id).where(query_sets.c.is_active == sa.true())
        )
    }
    feed_exists = bind.execute(
        sa.select(query_sets.c.id).where(query_sets.c.id == API_QUERY_SET_ID)
    ).first()
    if feed_exists is None:
        bind.execute(
            query_sets.insert().values(
                id=API_QUERY_SET_ID,
                name="API submissions",
                original_zip_name="api-submissions",
                is_active=True,
                created_at=datetime.now(UTC),
                created_by="system",
                import_status="complete",
            )
        )
    active_set_ids.add(API_QUERY_SET_ID)

    query_rows = list(
        bind.execute(
            sa.select(
                queries.c.id,
                queries.c.query_set_id,
                queries.c.file_name_key,
                queries.c.created_at,
            )
        ).mappings()
    )
    result_rows = list(
        bind.execute(
            sa.select(
                results.c.id,
                results.c.query_id,
                results.c.arrival_seq,
                results.c.created_at,
            )
        ).mappings()
    )
    results_by_query: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in result_rows:
        results_by_query[str(row["query_id"])].append(dict(row))

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in query_rows:
        grouped[str(row["file_name_key"])].append(dict(row))

    def group_first_received(item: tuple[str, list[dict[str, Any]]]) -> tuple[float, str]:
        key, rows = item
        received = [
            _timestamp(result["created_at"])
            for row in rows
            for result in results_by_query[str(row["id"])]
        ]
        created = [_timestamp(row["created_at"]) for row in rows]
        return (min(received or created or [float("inf")]), key)

    for display_order, (_, rows) in enumerate(
        sorted(grouped.items(), key=group_first_received), start=1
    ):
        target = min(
            rows,
            key=lambda row: (
                0 if str(row["query_set_id"]) in active_set_ids else 1,
                _timestamp(row["created_at"]),
                str(row["id"]),
            ),
        )
        target_id = str(target["id"])
        ordered_results = sorted(
            (result for row in rows for result in results_by_query[str(row["id"])]),
            key=lambda row: (
                _timestamp(row["created_at"]),
                int(row["arrival_seq"]),
                str(row["id"]),
            ),
        )
        for index, result in enumerate(ordered_results, start=1):
            bind.execute(
                results.update()
                .where(results.c.id == result["id"])
                .values(query_id=target_id, arrival_seq=-index)
            )
        for index, result in enumerate(ordered_results, start=1):
            bind.execute(
                results.update().where(results.c.id == result["id"]).values(arrival_seq=index)
            )
        duplicate_ids = [str(row["id"]) for row in rows if str(row["id"]) != target_id]
        if duplicate_ids:
            bind.execute(queries.delete().where(queries.c.id.in_(duplicate_ids)))
        bind.execute(
            queries.update()
            .where(queries.c.id == target_id)
            .values(
                query_set_id=API_QUERY_SET_ID,
                display_order=display_order,
                next_arrival_seq=len(ordered_results) + 1,
            )
        )

    bind.execute(query_sets.update().values(is_active=False))
    bind.execute(
        query_sets.update().where(query_sets.c.id == API_QUERY_SET_ID).values(is_active=True)
    )
    op.drop_constraint("uq_query_set_file_name", "queries", type_="unique")
    op.create_unique_constraint("uq_query_file_name_key", "queries", ["file_name_key"])


def downgrade() -> None:
    op.drop_constraint("uq_query_file_name_key", "queries", type_="unique")
    op.create_unique_constraint(
        "uq_query_set_file_name", "queries", ["query_set_id", "file_name_key"]
    )
