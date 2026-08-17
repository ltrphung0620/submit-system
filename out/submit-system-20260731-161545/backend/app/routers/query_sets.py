from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.errors import ApiError
from app.models import Query, QuerySet
from app.realtime import hub
from app.schemas import QuerySetRead
from app.security import Actor, get_actor
from app.services.query_import import parse_query_zip
from app.services.submissions import API_QUERY_SET_ID, get_or_create_api_query_set

router = APIRouter(prefix="/query-sets", tags=["query sets"])


@router.post("/import", status_code=201, response_model=QuerySetRead)
async def import_query_set(
    upload: UploadFile = File(...),
    name: str | None = Form(default=None),
    actor: Actor = Depends(get_actor),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> QuerySetRead:
    filename = upload.filename or "query-pack.zip"
    if not filename.casefold().endswith(".zip"):
        raise ApiError(422, "ZIP_REQUIRED", "Chỉ nhận file .zip")
    data = await upload.read(settings.max_zip_bytes + 1)
    if len(data) > settings.max_zip_bytes:
        raise ApiError(413, "ZIP_TOO_LARGE", "ZIP vượt giới hạn upload")
    parsed = parse_query_zip(data, settings)
    created_by = actor.name or "development"
    try:
        query_set = get_or_create_api_query_set(db, actor=created_by)
        query_set.name = (name or filename.removesuffix(".zip"))[:255]
        query_set.original_zip_name = filename[:255]
        query_set.created_by = created_by
        query_set.import_status = "complete"
        db.execute(update(QuerySet).where(QuerySet.id != API_QUERY_SET_ID).values(is_active=False))
        existing = {
            query.file_name_key: query
            for query in db.scalars(select(Query).where(Query.query_set_id == API_QUERY_SET_ID))
        }
        next_order = (
            db.scalar(
                select(func.max(Query.display_order)).where(Query.query_set_id == API_QUERY_SET_ID)
            )
            or 0
        )
        for item in parsed:
            query = existing.get(item.file_name_key)
            if query is not None:
                query.file_name = item.file_name
                query.query_type = item.query_type
                query.content = item.content
                query.source_path = item.source_path
                continue
            next_order += 1
            db.add(
                Query(
                    query_set_id=query_set.id,
                    file_name=item.file_name,
                    file_name_key=item.file_name_key,
                    query_type=item.query_type,
                    content=item.content,
                    display_order=next_order,
                    source_path=item.source_path,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    response = QuerySetRead(
        id=query_set.id,
        name=query_set.name,
        original_zip_name=query_set.original_zip_name,
        is_active=query_set.is_active,
        created_at=query_set.created_at,
        created_by=query_set.created_by,
        import_status=query_set.import_status,
        query_count=len(parsed),
    )
    await hub.publish("query_set_imported", response.model_dump(mode="json"))
    return response


@router.get("", response_model=list[QuerySetRead])
def list_query_sets(db: Session = Depends(get_db)) -> list[QuerySetRead]:
    query_count = (
        select(func.count(Query.id))
        .where(Query.query_set_id == QuerySet.id)
        .correlate(QuerySet)
        .scalar_subquery()
    )
    rows = db.execute(select(QuerySet, query_count).order_by(QuerySet.created_at.desc())).all()
    return [
        QuerySetRead(
            id=query_set.id,
            name=query_set.name,
            original_zip_name=query_set.original_zip_name,
            is_active=query_set.is_active,
            created_at=query_set.created_at,
            created_by=query_set.created_by,
            import_status=query_set.import_status,
            query_count=count,
        )
        for query_set, count in rows
    ]
