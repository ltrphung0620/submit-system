from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Query, QuerySet
from app.services.validation import canonical_file_name, infer_query_type

API_QUERY_SET_ID = "00000000-0000-0000-0000-000000000001"


def get_or_create_api_query_set(db: Session, *, actor: str) -> QuerySet:
    query_set = db.get(QuerySet, API_QUERY_SET_ID)
    if query_set is None:
        db.execute(update(QuerySet).values(is_active=False))
        query_set = QuerySet(
            id=API_QUERY_SET_ID,
            name="API submissions",
            original_zip_name="api-submissions",
            is_active=True,
            created_by=actor,
            import_status="complete",
        )
        db.add(query_set)
        db.flush()
    elif not query_set.is_active:
        db.execute(update(QuerySet).values(is_active=False))
        query_set.is_active = True
        db.flush()
    return query_set


def find_submission_query(db: Session, file_name: str) -> Query | None:
    return db.scalar(select(Query).where(Query.file_name_key == canonical_file_name(file_name)))


def create_submission_query(
    db: Session, *, file_name: str, query_content: str, actor: str
) -> Query:
    query_set = get_or_create_api_query_set(db, actor=actor)
    display_order = (
        db.scalar(
            select(func.max(Query.display_order)).where(Query.query_set_id == API_QUERY_SET_ID)
        )
        or 0
    ) + 1
    query = Query(
        query_set_id=query_set.id,
        file_name=file_name,
        file_name_key=canonical_file_name(file_name),
        query_type=infer_query_type(file_name),
        content=query_content,
        display_order=display_order,
        source_path="api-submission",
    )
    db.add(query)
    db.flush()
    return query
