"""Initial schema."""

import sqlalchemy as sa
from alembic import op

revision = "20260722_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "query_sets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("original_zip_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("import_status", sa.String(32), nullable=False),
    )
    op.create_index("ix_query_sets_is_active", "query_sets", ["is_active"])
    op.create_table(
        "queries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "query_set_id",
            sa.String(36),
            sa.ForeignKey("query_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_name_key", sa.String(255), nullable=False),
        sa.Column("query_type", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("source_path", sa.String(1024), nullable=False),
        sa.Column("next_arrival_seq", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("query_set_id", "file_name_key", name="uq_query_set_file_name"),
    )
    op.create_index("ix_queries_query_type", "queries", ["query_type"])
    op.create_index("ix_queries_set_type", "queries", ["query_set_id", "query_type"])
    op.create_table(
        "result_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "query_id",
            sa.String(36),
            sa.ForeignKey("queries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("arrival_seq", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(255), nullable=False),
        sa.Column("frame_ids", sa.JSON(), nullable=False),
        sa.Column("answer", sa.Text()),
        sa.Column("submitter", sa.String(255), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_by", sa.String(255)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("structural_validation_status", sa.String(32), nullable=False),
        sa.Column("official_validation_status", sa.String(32), nullable=False),
        sa.UniqueConstraint("query_id", "arrival_seq", name="uq_query_arrival_seq"),
    )
    op.create_index("ix_results_query_deleted", "result_candidates", ["query_id", "deleted_at"])
    op.create_index("ix_results_submitter", "result_candidates", ["submitter"])
    op.create_index(
        "ix_results_submitter_created", "result_candidates", ["submitter", "created_at"]
    )
    op.create_table(
        "image_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "result_candidate_id",
            sa.String(36),
            sa.ForeignKey("result_candidates.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("original_mime_type", sa.String(100)),
        sa.Column("detected_mime_type", sa.String(100), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_image_attachments_sha256", "image_attachments", ["sha256"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("old_value", sa.JSON()),
        sa.Column("new_value", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_table(
        "export_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("query_set_id", sa.String(36), sa.ForeignKey("query_sets.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("format_verification_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archive_path", sa.String(512), nullable=False),
        sa.Column("validation_report", sa.JSON(), nullable=False),
        sa.Column("source_data_version", sa.String(64), nullable=False),
    )
    op.create_index(
        "ix_exports_query_set_created", "export_snapshots", ["query_set_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("export_snapshots")
    op.drop_table("audit_logs")
    op.drop_table("image_attachments")
    op.drop_table("result_candidates")
    op.drop_table("queries")
    op.drop_table("query_sets")
