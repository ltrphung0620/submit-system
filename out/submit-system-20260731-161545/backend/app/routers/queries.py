from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import Select, select, true
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.errors import ApiError
from app.models import Query, QuerySet, ResultCandidate
from app.schemas import QueryRead, ResultRead
from app.serializers import query_read, result_read

router = APIRouter(prefix="/queries", tags=["queries"])


def query_statement() -> Select[tuple[Query]]:
    return (
        select(Query)
        .join(QuerySet)
        .where(QuerySet.is_active == true())
        .options(joinedload(Query.results).joinedload(ResultCandidate.image))
        .order_by(Query.display_order)
    )


@router.get("", response_model=list[QueryRead])
def list_queries(db: Session = Depends(get_db)) -> list[QueryRead]:
    queries = db.scalars(query_statement()).unique().all()
    return [query_read(query) for query in queries]


@router.get("/{query_id}", response_model=QueryRead)
def get_query(query_id: str, db: Session = Depends(get_db)) -> QueryRead:
    query = db.scalar(
        select(Query)
        .where(Query.id == query_id)
        .options(joinedload(Query.results).joinedload(ResultCandidate.image))
    )
    if query is None:
        raise ApiError(404, "QUERY_NOT_FOUND", "Không tìm thấy query")
    return query_read(query)


@router.get("/{query_id}/results", response_model=list[ResultRead])
def get_query_results(query_id: str, db: Session = Depends(get_db)) -> list[ResultRead]:
    query = db.scalar(
        select(Query)
        .where(Query.id == query_id)
        .options(joinedload(Query.results).joinedload(ResultCandidate.image))
    )
    if query is None:
        raise ApiError(404, "QUERY_NOT_FOUND", "Không tìm thấy query")
    return [
        result_read(result, query)
        for result in sorted(query.results, key=lambda item: (item.priority, item.arrival_seq))
        if result.deleted_at is None
    ]
