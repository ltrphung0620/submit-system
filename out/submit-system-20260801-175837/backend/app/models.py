from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Unicode,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


class QuerySet(Base):
    __tablename__ = "query_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(Unicode(255))
    original_zip_name: Mapped[str] = mapped_column(Unicode(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_by: Mapped[str] = mapped_column(Unicode(255))
    import_status: Mapped[str] = mapped_column(String(32), default="complete")

    queries: Mapped[list[Query]] = relationship(back_populates="query_set", cascade="all, delete")


class Query(Base):
    __tablename__ = "queries"
    __table_args__ = (
        UniqueConstraint("file_name_key", name="uq_query_file_name_key"),
        Index("ix_queries_set_type", "query_set_id", "query_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    query_set_id: Mapped[str] = mapped_column(ForeignKey("query_sets.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(Unicode(255))
    file_name_key: Mapped[str] = mapped_column(Unicode(255))
    query_type: Mapped[str] = mapped_column(String(16), index=True)
    content: Mapped[str] = mapped_column(Unicode())
    display_order: Mapped[int] = mapped_column(Integer)
    source_path: Mapped[str] = mapped_column(Unicode(1024))
    next_arrival_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    query_set: Mapped[QuerySet] = relationship(back_populates="queries")
    results: Mapped[list[ResultCandidate]] = relationship(
        back_populates="query", cascade="all, delete"
    )


class ResultCandidate(Base):
    __tablename__ = "result_candidates"
    __table_args__ = (
        UniqueConstraint("query_id", "arrival_seq", name="uq_query_arrival_seq"),
        Index(
            "ux_active_query_priority",
            "query_id",
            "priority",
            unique=True,
            mssql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_results_query_deleted", "query_id", "deleted_at"),
        Index("ix_results_submitter_created", "submitter", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    query_id: Mapped[str] = mapped_column(ForeignKey("queries.id", ondelete="CASCADE"))
    arrival_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    video_id: Mapped[str] = mapped_column(Unicode(255))
    frame_ids: Mapped[list[int]] = mapped_column(JSON)
    answer: Mapped[str | None] = mapped_column(Unicode())
    submitter: Mapped[str] = mapped_column(Unicode(255), index=True)
    note: Mapped[str | None] = mapped_column(Unicode())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[str | None] = mapped_column(Unicode(255))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    structural_validation_status: Mapped[str] = mapped_column(String(32), default="valid")
    official_validation_status: Mapped[str] = mapped_column(String(32), default="unverified")

    query: Mapped[Query] = relationship(back_populates="results")
    image: Mapped[ImageAttachment | None] = relationship(
        back_populates="result", cascade="all, delete", uselist=False
    )


class ImageAttachment(Base):
    __tablename__ = "image_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    result_candidate_id: Mapped[str] = mapped_column(
        ForeignKey("result_candidates.id", ondelete="CASCADE"), unique=True
    )
    original_mime_type: Mapped[str | None] = mapped_column(String(100))
    detected_mime_type: Mapped[str] = mapped_column(String(100))
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    byte_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    result: Mapped[ResultCandidate] = relationship(back_populates="image")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    action: Mapped[str] = mapped_column(String(32))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(36))
    actor: Mapped[str] = mapped_column(Unicode(255))
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExportSnapshot(Base):
    __tablename__ = "export_snapshots"
    __table_args__ = (Index("ix_exports_query_set_created", "query_set_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    query_set_id: Mapped[str] = mapped_column(ForeignKey("query_sets.id"))
    status: Mapped[str] = mapped_column(String(32))
    format_verification_status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archive_path: Mapped[str] = mapped_column(String(512))
    validation_report: Mapped[dict[str, Any]] = mapped_column(JSON)
    source_data_version: Mapped[str] = mapped_column(String(64))
