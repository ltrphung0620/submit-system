"""Store user-visible content as Unicode on SQL Server."""

import sqlalchemy as sa
from alembic import op

revision = "20260722_0003"
down_revision = "20260722_0002"
branch_labels = None
depends_on = None

UNICODE_COLUMNS = {
    "query_sets": (
        ("name", 255, False),
        ("original_zip_name", 255, False),
        ("created_by", 255, False),
    ),
    "queries": (
        ("file_name", 255, False),
        ("file_name_key", 255, False),
        ("content", None, False),
        ("source_path", 1024, False),
    ),
    "result_candidates": (
        ("video_id", 255, False),
        ("answer", None, True),
        ("submitter", 255, False),
        ("note", None, True),
        ("deleted_by", 255, True),
    ),
    "audit_logs": (("actor", 255, False),),
}


def upgrade() -> None:
    op.drop_constraint("uq_query_set_file_name", "queries", type_="unique")
    op.drop_index("ix_result_candidates_submitter", table_name="result_candidates")
    op.drop_index("ix_results_submitter_created", table_name="result_candidates")
    for table, columns in UNICODE_COLUMNS.items():
        for column, length, nullable in columns:
            existing_type: sa.TypeEngine = sa.Text() if length is None else sa.String(length)
            op.alter_column(
                table,
                column,
                existing_type=existing_type,
                type_=sa.Unicode(length),
                existing_nullable=nullable,
            )
    op.create_unique_constraint(
        "uq_query_set_file_name", "queries", ["query_set_id", "file_name_key"]
    )
    op.create_index("ix_result_candidates_submitter", "result_candidates", ["submitter"])
    op.create_index(
        "ix_results_submitter_created",
        "result_candidates",
        ["submitter", "created_at"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_query_set_file_name", "queries", type_="unique")
    op.drop_index("ix_result_candidates_submitter", table_name="result_candidates")
    op.drop_index("ix_results_submitter_created", table_name="result_candidates")
    for table, columns in UNICODE_COLUMNS.items():
        for column, length, nullable in columns:
            existing_type: sa.TypeEngine = sa.Unicode(length)
            target_type: sa.TypeEngine = sa.Text() if length is None else sa.String(length)
            op.alter_column(
                table,
                column,
                existing_type=existing_type,
                type_=target_type,
                existing_nullable=nullable,
            )
    op.create_unique_constraint(
        "uq_query_set_file_name", "queries", ["query_set_id", "file_name_key"]
    )
    op.create_index("ix_result_candidates_submitter", "result_candidates", ["submitter"])
    op.create_index(
        "ix_results_submitter_created",
        "result_candidates",
        ["submitter", "created_at"],
    )
