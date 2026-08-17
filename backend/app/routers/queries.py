from __future__ import annotations

from contextlib import suppress

from fastapi import APIRouter, Depends, Response
from sqlalchemy import Select, select, true
from sqlalchemy.orm import Session, joinedload

from app.config import Settings, get_settings
from app.database import get_db
from app.errors import ApiError
from app.models import AuditLog, Query, QuerySet, ResultCandidate
from app.realtime import hub
from app.schemas import QueryRead, ResultRead
from app.security import Actor, get_actor, require_mutation_permission
from app.serializers import query_read, result_read
from app.services.images import LocalImageStorage

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


@router.delete("", status_code=204)
async def delete_all_queries(
    actor: Actor = Depends(get_actor),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> Response:
    queries = (
        db.scalars(
            select(Query)
            .join(QuerySet)
            .where(QuerySet.is_active == true())
            .options(
                joinedload(Query.query_set),
                joinedload(Query.results).joinedload(ResultCandidate.image),
            )
        )
        .unique()
        .all()
    )
    image_keys: list[str] = []
    for query in queries:
        acting_name = require_mutation_permission(actor, query.query_set.created_by, settings)
        image_keys.extend(result.image.storage_key for result in query.results if result.image)
        db.add(
            AuditLog(
                action="deleted",
                entity_type="query",
                entity_id=query.id,
                actor=acting_name,
                old_value={
                    "file_name": query.file_name,
                    "candidate_count": len(query.results),
                },
                new_value=None,
            )
        )
        db.delete(query)
    db.commit()

    storage = LocalImageStorage(settings.storage_root)
    for storage_key in image_keys:
        with suppress(OSError):
            storage.delete(storage_key)
    await hub.publish("query_deleted", {"all": True})
    return Response(status_code=204)


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


@router.delete("/{query_id}", status_code=204)
async def delete_query(
    query_id: str,
    actor: Actor = Depends(get_actor),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> Response:
    query = (
        db.scalars(
            select(Query)
            .join(QuerySet)
            .where(Query.id == query_id, QuerySet.is_active == true())
            .options(
                joinedload(Query.query_set),
                joinedload(Query.results).joinedload(ResultCandidate.image),
            )
        )
        .unique()
        .one_or_none()
    )
    if query is None:
        raise ApiError(404, "QUERY_NOT_FOUND", "Không tìm thấy query")

    acting_name = require_mutation_permission(actor, query.query_set.created_by, settings)
    image_keys = [result.image.storage_key for result in query.results if result.image]
    db.add(
        AuditLog(
            action="deleted",
            entity_type="query",
            entity_id=query.id,
            actor=acting_name,
            old_value={
                "file_name": query.file_name,
                "candidate_count": len(query.results),
            },
            new_value=None,
        )
    )
    db.delete(query)
    db.commit()

    storage = LocalImageStorage(settings.storage_root)
    for storage_key in image_keys:
        with suppress(OSError):
            storage.delete(storage_key)
    await hub.publish("query_deleted", {"id": query_id})
    return Response(status_code=204)
