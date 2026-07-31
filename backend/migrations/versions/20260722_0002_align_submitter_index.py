"""Align submitter index name with SQLAlchemy metadata."""

from alembic import op

revision = "20260722_0002"
down_revision = "20260722_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_results_submitter", table_name="result_candidates")
    op.create_index("ix_result_candidates_submitter", "result_candidates", ["submitter"])


def downgrade() -> None:
    op.drop_index("ix_result_candidates_submitter", table_name="result_candidates")
    op.create_index("ix_results_submitter", "result_candidates", ["submitter"])
