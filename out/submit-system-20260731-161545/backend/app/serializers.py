from __future__ import annotations

from app.models import Query, ResultCandidate
from app.schemas import QueryRead, ResultRead


def result_read(result: ResultCandidate, query: Query | None = None) -> ResultRead:
    owning_query = query or result.query
    image = result.image
    return ResultRead(
        id=result.id,
        query_id=result.query_id,
        file_name=owning_query.file_name,
        query_type=owning_query.query_type,
        arrival_seq=result.arrival_seq,
        priority=result.priority,
        video_id=result.video_id,
        img_id=result.frame_ids if owning_query.query_type == "trake" else result.frame_ids[0],
        answer=result.answer,
        submitter=result.submitter,
        note=result.note,
        created_at=result.created_at,
        updated_at=result.updated_at,
        version=result.version,
        structural_validation_status=result.structural_validation_status,
        official_validation_status=result.official_validation_status,
        image_url=f"/api/v1/images/{image.id}" if image else None,
        image_mime_type=image.detected_mime_type if image else None,
    )


def query_read(query: Query) -> QueryRead:
    active = sorted(
        (result for result in query.results if result.deleted_at is None),
        key=lambda item: (item.priority, item.arrival_seq),
    )
    return QueryRead(
        id=query.id,
        query_set_id=query.query_set_id,
        file_name=query.file_name,
        query_type=query.query_type,
        content=query.content,
        display_order=query.display_order,
        source_path=query.source_path,
        results=[result_read(result, query) for result in active],
    )
