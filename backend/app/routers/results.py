from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from fastapi import Query as QueryParameter
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import Settings, get_settings
from app.database import get_db
from app.errors import ApiError
from app.models import AuditLog, ImageAttachment, Query, ResultCandidate
from app.realtime import hub
from app.schemas import PriorityReorder, PrioritySwap, ResultCreate, ResultPatch, ResultRead
from app.security import (
    Actor,
    get_actor,
    require_mutation_permission,
    require_submitter,
)
from app.serializers import result_read
from app.services.images import DecodedImage, LocalImageStorage, decode_image
from app.services.submissions import create_submission_query, find_submission_query
from app.services.validation import (
    infer_query_type,
    validate_query_content,
    validate_result_payload,
)

router = APIRouter(prefix="/results", tags=["results"])
public_router = APIRouter(prefix="/submissions", tags=["public submissions"])


def load_result(db: Session, result_id: str) -> ResultCandidate:
    result = db.scalar(
        select(ResultCandidate)
        .where(ResultCandidate.id == result_id, ResultCandidate.deleted_at.is_(None))
        .options(joinedload(ResultCandidate.query), joinedload(ResultCandidate.image))
    )
    if result is None:
        raise ApiError(404, "RESULT_NOT_FOUND", "Không tìm thấy kết quả")
    return result


@router.post(
    "",
    status_code=201,
    response_model=ResultRead,
    summary="Nhận một kết quả KIS, QA hoặc TRAKE",
)
@public_router.post(
    "",
    status_code=201,
    response_model=ResultRead,
    summary="Nhận một submission từ hệ thống bên ngoài",
    description=(
        "Loại submission được suy ra từ hậu tố -kis, -qa hoặc -trake của file_name. "
        "file_name mới tự động tạo một nhóm trên UI; các request trùng file_name được "
        "xếp theo arrival_seq."
    ),
)
async def create_result(
    payload: ResultCreate,
    actor: Actor = Depends(get_actor),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> ResultRead:
    submitter = require_submitter(actor, payload.submitter)
    request_query_type = infer_query_type(payload.file_name)
    query_content = validate_query_content(payload.query_content)
    frame_ids, answer = validate_result_payload(
        request_query_type,
        file_name=payload.file_name,
        img_id=payload.img_id,
        video_id=payload.video_id,
        submitter=submitter,
        answer=payload.answer,
    )
    query = find_submission_query(db, payload.file_name)
    if query is None:
        try:
            query = create_submission_query(
                db,
                file_name=payload.file_name,
                query_content=query_content,
                actor=submitter,
            )
        except IntegrityError:
            db.rollback()
            query = find_submission_query(db, payload.file_name)
            if query is None:
                raise
    elif query.query_type != request_query_type:
        raise ApiError(
            409,
            "QUERY_TYPE_MISMATCH",
            "file_name đã được đăng ký với một loại query khác",
        )
    decoded = None
    if payload.image_base64 is not None:
        decoded = decode_image(
            payload.image_base64, payload.image_mime_type, settings.max_image_bytes
        )
    elif payload.image_mime_type is not None:
        raise ApiError(422, "IMAGE_DATA_REQUIRED", "image_mime_type yêu cầu image_base64")

    storage = LocalImageStorage(settings.storage_root)
    stored_key: str | None = None
    try:
        next_value = db.execute(
            update(Query)
            .where(Query.id == query.id)
            .values(next_arrival_seq=Query.next_arrival_seq + 1)
            .returning(Query.next_arrival_seq)
        ).scalar_one()
        next_priority = (
            db.scalar(
                select(func.max(ResultCandidate.priority)).where(
                    ResultCandidate.query_id == query.id,
                    ResultCandidate.deleted_at.is_(None),
                )
            )
            or 0
        ) + 1
        candidate = ResultCandidate(
            query_id=query.id,
            arrival_seq=next_value - 1,
            priority=next_priority,
            video_id=payload.video_id,
            frame_ids=frame_ids,
            answer=answer,
            submitter=submitter,
            note=payload.note,
        )
        db.add(candidate)
        db.flush()
        if decoded:
            stored_key = storage.save(decoded)
            db.add(
                ImageAttachment(
                    result_candidate_id=candidate.id,
                    original_mime_type=decoded.supplied_mime,
                    detected_mime_type=decoded.detected_mime,
                    storage_key=stored_key,
                    byte_size=len(decoded.data),
                    sha256=decoded.sha256,
                )
            )
        db.add(
            AuditLog(
                action="created",
                entity_type="result_candidate",
                entity_id=candidate.id,
                actor=submitter,
                old_value=None,
                new_value={
                    "file_name": query.file_name,
                    "query_type": query.query_type,
                    "query_id": query.id,
                    "arrival_seq": candidate.arrival_seq,
                    "priority": candidate.priority,
                    "video_id": candidate.video_id,
                    "frame_ids": candidate.frame_ids,
                    "answer": candidate.answer,
                    "submitter": candidate.submitter,
                    "note": candidate.note,
                },
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        if stored_key:
            storage.delete(stored_key)
        raise
    candidate = load_result(db, candidate.id)
    response = result_read(candidate)
    await hub.publish("created", response.model_dump(mode="json"))
    return response


@router.post(
    "/priority/swap",
    response_model=list[ResultRead],
    summary="Đổi priority giữa hai submission trong cùng một nhóm",
)
async def swap_result_priorities(
    payload: PrioritySwap,
    actor: Actor = Depends(get_actor),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> list[ResultRead]:
    if payload.first_result_id == payload.second_result_id:
        raise ApiError(422, "SWAP_REQUIRES_TWO_RESULTS", "Cần hai submission khác nhau")
    first = load_result(db, payload.first_result_id)
    second = load_result(db, payload.second_result_id)
    if first.query_id != second.query_id:
        raise ApiError(
            422,
            "SWAP_QUERY_MISMATCH",
            "Chỉ có thể đổi priority trong cùng một file_name",
        )
    locked = db.execute(
        update(Query)
        .where(Query.id == first.query_id)
        .values(display_order=Query.display_order)
        .execution_options(synchronize_session=False)
    ).rowcount
    if locked != 1:
        db.rollback()
        raise ApiError(404, "QUERY_NOT_FOUND", "Không tìm thấy nhóm submission")
    acting_name = require_mutation_permission(actor, first.submitter, settings)
    require_mutation_permission(actor, second.submitter, settings)
    first_priority = first.priority
    second_priority = second.priority
    if first_priority == second_priority:
        raise ApiError(409, "PRIORITY_CONFLICT", "Hai submission đang trùng priority")
    changed_at = datetime.now(UTC)
    temporary_priority = -(
        max(first_priority, second_priority, first.arrival_seq, second.arrival_seq) + 1
    )
    try:
        moved_first = db.execute(
            update(ResultCandidate)
            .where(
                ResultCandidate.id == first.id,
                ResultCandidate.version == payload.expected_first_version,
                ResultCandidate.deleted_at.is_(None),
            )
            .values(priority=temporary_priority)
            .execution_options(synchronize_session=False)
        ).rowcount
        if moved_first != 1:
            raise ApiError(
                409,
                "VERSION_CONFLICT",
                "Submission thứ nhất đã được thay đổi bởi client khác",
            )
        moved_second = db.execute(
            update(ResultCandidate)
            .where(
                ResultCandidate.id == second.id,
                ResultCandidate.version == payload.expected_second_version,
                ResultCandidate.deleted_at.is_(None),
            )
            .values(
                priority=first_priority,
                version=ResultCandidate.version + 1,
                updated_at=changed_at,
            )
            .execution_options(synchronize_session=False)
        ).rowcount
        if moved_second != 1:
            raise ApiError(
                409,
                "VERSION_CONFLICT",
                "Submission thứ hai đã được thay đổi bởi client khác",
            )
        finalized_first = db.execute(
            update(ResultCandidate)
            .where(
                ResultCandidate.id == first.id,
                ResultCandidate.version == payload.expected_first_version,
                ResultCandidate.priority == temporary_priority,
                ResultCandidate.deleted_at.is_(None),
            )
            .values(
                priority=second_priority,
                version=ResultCandidate.version + 1,
                updated_at=changed_at,
            )
            .execution_options(synchronize_session=False)
        ).rowcount
        if finalized_first != 1:
            raise ApiError(409, "VERSION_CONFLICT", "Không thể hoàn tất đổi priority")
        db.add_all(
            [
                AuditLog(
                    action="priority_swapped",
                    entity_type="result_candidate",
                    entity_id=first.id,
                    actor=acting_name,
                    old_value={
                        "priority": first_priority,
                        "arrival_seq": first.arrival_seq,
                        "version": payload.expected_first_version,
                    },
                    new_value={
                        "priority": second_priority,
                        "arrival_seq": first.arrival_seq,
                    },
                ),
                AuditLog(
                    action="priority_swapped",
                    entity_type="result_candidate",
                    entity_id=second.id,
                    actor=acting_name,
                    old_value={
                        "priority": second_priority,
                        "arrival_seq": second.arrival_seq,
                        "version": payload.expected_second_version,
                    },
                    new_value={
                        "priority": first_priority,
                        "arrival_seq": second.arrival_seq,
                    },
                ),
            ]
        )
        db.commit()
        db.expire_all()
    except ApiError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "PRIORITY_CONFLICT",
            "Priority vừa được thay đổi bởi thao tác khác",
        ) from exc
    responses = [
        result_read(load_result(db, first.id)),
        result_read(load_result(db, second.id)),
    ]
    responses.sort(key=lambda item: (item.priority, item.arrival_seq))
    for response in responses:
        await hub.publish("updated", response.model_dump(mode="json"))
    return responses


@router.post(
    "/priority/reorder",
    response_model=list[ResultRead],
    summary="Sắp lại priority theo thứ tự kéo thả",
)
async def reorder_result_priorities(
    payload: PriorityReorder,
    actor: Actor = Depends(get_actor),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> list[ResultRead]:
    ordered_ids = list(payload.ordered_result_ids)
    if len(set(ordered_ids)) != len(ordered_ids):
        raise ApiError(422, "DUPLICATE_RESULT_ID", "Danh sách priority chứa ID trùng")
    locked = db.execute(
        update(Query)
        .where(Query.id == payload.query_id)
        .values(display_order=Query.display_order)
        .execution_options(synchronize_session=False)
    ).rowcount
    if locked != 1:
        db.rollback()
        raise ApiError(404, "QUERY_NOT_FOUND", "Không tìm thấy nhóm submission")
    current_results = (
        db.scalars(
            select(ResultCandidate)
            .where(
                ResultCandidate.query_id == payload.query_id,
                ResultCandidate.deleted_at.is_(None),
            )
            .options(joinedload(ResultCandidate.query), joinedload(ResultCandidate.image))
        )
        .unique()
        .all()
    )
    by_id = {result.id: result for result in current_results}
    if set(ordered_ids) != set(by_id):
        db.rollback()
        raise ApiError(
            409,
            "STALE_PRIORITY_ORDER",
            "Danh sách submission đã thay đổi; hãy tải lại trước khi kéo",
        )
    if set(payload.expected_versions) != set(by_id):
        db.rollback()
        raise ApiError(
            422,
            "EXPECTED_VERSIONS_MISMATCH",
            "expected_versions phải chứa đủ các submission trong nhóm",
        )
    acting_name: str | None = None
    for result in current_results:
        acting_name = acting_name or require_mutation_permission(actor, result.submitter, settings)
        require_mutation_permission(actor, result.submitter, settings)
        if result.version != payload.expected_versions[result.id]:
            db.rollback()
            raise ApiError(
                409,
                "VERSION_CONFLICT",
                "Submission đã được thay đổi bởi client khác",
            )
    available_priorities = sorted(result.priority for result in current_results)
    final_priority = dict(zip(ordered_ids, available_priorities, strict=True))
    changed = [result for result in current_results if result.priority != final_priority[result.id]]
    if not changed:
        db.rollback()
        return [
            result_read(result)
            for result in sorted(
                current_results,
                key=lambda item: (item.priority, item.arrival_seq),
            )
        ]
    changed_at = datetime.now(UTC)
    temporary_base = max(
        [abs(result.priority) for result in current_results]
        + [result.arrival_seq for result in current_results]
    )
    try:
        for offset, result in enumerate(changed, start=1):
            moved = db.execute(
                update(ResultCandidate)
                .where(
                    ResultCandidate.id == result.id,
                    ResultCandidate.version == payload.expected_versions[result.id],
                    ResultCandidate.priority == result.priority,
                    ResultCandidate.deleted_at.is_(None),
                )
                .values(priority=-(temporary_base + offset))
                .execution_options(synchronize_session=False)
            ).rowcount
            if moved != 1:
                raise ApiError(
                    409,
                    "VERSION_CONFLICT",
                    "Submission đã được thay đổi trong lúc sắp xếp",
                )
        for result in changed:
            finalized = db.execute(
                update(ResultCandidate)
                .where(
                    ResultCandidate.id == result.id,
                    ResultCandidate.version == payload.expected_versions[result.id],
                    ResultCandidate.deleted_at.is_(None),
                )
                .values(
                    priority=final_priority[result.id],
                    version=ResultCandidate.version + 1,
                    updated_at=changed_at,
                )
                .execution_options(synchronize_session=False)
            ).rowcount
            if finalized != 1:
                raise ApiError(
                    409,
                    "VERSION_CONFLICT",
                    "Không thể hoàn tất thứ tự priority mới",
                )
            db.add(
                AuditLog(
                    action="priority_reordered",
                    entity_type="result_candidate",
                    entity_id=result.id,
                    actor=acting_name or result.submitter,
                    old_value={
                        "priority": result.priority,
                        "arrival_seq": result.arrival_seq,
                        "version": payload.expected_versions[result.id],
                    },
                    new_value={
                        "priority": final_priority[result.id],
                        "arrival_seq": result.arrival_seq,
                    },
                )
            )
        db.commit()
        db.expire_all()
    except ApiError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "PRIORITY_CONFLICT",
            "Priority vừa được thay đổi bởi thao tác khác",
        ) from exc
    responses = [result_read(load_result(db, result_id)) for result_id in ordered_ids]
    changed_ids = {result.id for result in changed}
    for response in responses:
        if response.id in changed_ids:
            await hub.publish("updated", response.model_dump(mode="json"))
    return responses


@router.get("/{result_id}", response_model=ResultRead)
def get_result(result_id: str, db: Session = Depends(get_db)) -> ResultRead:
    return result_read(load_result(db, result_id))


@router.post("/{result_id}/duplicate", status_code=201, response_model=ResultRead)
async def duplicate_result(
    result_id: str,
    actor: Actor = Depends(get_actor),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> ResultRead:
    current = load_result(db, result_id)
    acting_name = require_mutation_permission(actor, current.submitter, settings)
    storage = LocalImageStorage(settings.storage_root)
    stored_key: str | None = None
    try:
        next_value = db.execute(
            update(Query)
            .where(Query.id == current.query_id)
            .values(next_arrival_seq=Query.next_arrival_seq + 1)
            .returning(Query.next_arrival_seq)
        ).scalar_one()
        next_priority = (
            db.scalar(
                select(func.max(ResultCandidate.priority)).where(
                    ResultCandidate.query_id == current.query_id,
                    ResultCandidate.deleted_at.is_(None),
                )
            )
            or 0
        ) + 1
        duplicate = ResultCandidate(
            query_id=current.query_id,
            arrival_seq=next_value - 1,
            priority=next_priority,
            video_id=current.video_id,
            frame_ids=list(current.frame_ids),
            answer=current.answer,
            submitter=current.submitter,
            note=current.note,
        )
        db.add(duplicate)
        db.flush()
        if current.image:
            image_data = storage.read(current.image.storage_key)
            cloned_image = DecodedImage(
                data=image_data,
                supplied_mime=current.image.original_mime_type,
                detected_mime=current.image.detected_mime_type,
                sha256=hashlib.sha256(image_data).hexdigest(),
            )
            stored_key = storage.save(cloned_image)
            db.add(
                ImageAttachment(
                    result_candidate_id=duplicate.id,
                    original_mime_type=cloned_image.supplied_mime,
                    detected_mime_type=cloned_image.detected_mime,
                    storage_key=stored_key,
                    byte_size=len(cloned_image.data),
                    sha256=cloned_image.sha256,
                )
            )
        db.add(
            AuditLog(
                action="duplicated",
                entity_type="result_candidate",
                entity_id=duplicate.id,
                actor=acting_name,
                old_value={"source_result_id": current.id},
                new_value={
                    "query_id": duplicate.query_id,
                    "arrival_seq": duplicate.arrival_seq,
                    "priority": duplicate.priority,
                },
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        if stored_key:
            storage.delete(stored_key)
        raise
    response = result_read(load_result(db, duplicate.id))
    await hub.publish("created", response.model_dump(mode="json"))
    return response


@router.patch("/{result_id}", response_model=ResultRead)
async def update_result(
    result_id: str,
    payload: ResultPatch,
    actor: Actor = Depends(get_actor),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> ResultRead:
    current = load_result(db, result_id)
    acting_name = require_mutation_permission(actor, current.submitter, settings)
    fields = payload.model_fields_set
    img_id = (
        payload.img_id
        if "img_id" in fields
        else current.frame_ids
        if current.query.query_type == "trake"
        else current.frame_ids[0]
    )
    video_id = payload.video_id if "video_id" in fields else current.video_id
    answer = payload.answer if "answer" in fields else current.answer
    frame_ids, validated_answer = validate_result_payload(
        current.query.query_type,
        file_name=current.query.file_name,
        img_id=img_id,
        video_id=video_id,
        submitter=current.submitter,
        answer=answer,
    )
    note = payload.note if "note" in fields else current.note
    old_value = {
        "video_id": current.video_id,
        "frame_ids": current.frame_ids,
        "answer": current.answer,
        "note": current.note,
        "version": current.version,
    }
    changed = db.execute(
        update(ResultCandidate)
        .where(
            ResultCandidate.id == result_id,
            ResultCandidate.deleted_at.is_(None),
            ResultCandidate.version == payload.expected_version,
        )
        .values(
            video_id=video_id,
            frame_ids=frame_ids,
            answer=validated_answer,
            note=note,
            version=ResultCandidate.version + 1,
            updated_at=datetime.now(UTC),
        )
    ).rowcount
    if changed != 1:
        db.rollback()
        raise ApiError(409, "VERSION_CONFLICT", "Kết quả đã được thay đổi bởi client khác")
    db.add(
        AuditLog(
            action="updated",
            entity_type="result_candidate",
            entity_id=result_id,
            actor=acting_name,
            old_value=old_value,
            new_value={"video_id": video_id, "frame_ids": frame_ids, "answer": validated_answer},
        )
    )
    db.commit()
    response = result_read(load_result(db, result_id))
    await hub.publish("updated", response.model_dump(mode="json"))
    return response


@router.delete("/{result_id}", status_code=204)
async def delete_result(
    result_id: str,
    expected_version: int = QueryParameter(..., ge=1),
    actor: Actor = Depends(get_actor),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> Response:
    current = load_result(db, result_id)
    acting_name = require_mutation_permission(actor, current.submitter, settings)
    deleted_at = datetime.now(UTC)
    locked = db.execute(
        update(Query)
        .where(Query.id == current.query_id)
        .values(display_order=Query.display_order)
        .execution_options(synchronize_session=False)
    ).rowcount
    if locked != 1:
        db.rollback()
        raise ApiError(404, "QUERY_NOT_FOUND", "Không tìm thấy nhóm submission")
    shifted = list(
        db.scalars(
            select(ResultCandidate)
            .where(
                ResultCandidate.query_id == current.query_id,
                ResultCandidate.deleted_at.is_(None),
                ResultCandidate.priority > current.priority,
            )
            .order_by(ResultCandidate.priority)
        )
    )
    changed = db.execute(
        update(ResultCandidate)
        .where(
            ResultCandidate.id == result_id,
            ResultCandidate.deleted_at.is_(None),
            ResultCandidate.version == expected_version,
        )
        .values(
            deleted_at=deleted_at,
            deleted_by=acting_name,
            version=ResultCandidate.version + 1,
            updated_at=deleted_at,
        )
    ).rowcount
    if changed != 1:
        db.rollback()
        raise ApiError(409, "VERSION_CONFLICT", "Kết quả đã được thay đổi bởi client khác")
    for result in shifted:
        compacted = db.execute(
            update(ResultCandidate)
            .where(
                ResultCandidate.id == result.id,
                ResultCandidate.deleted_at.is_(None),
                ResultCandidate.version == result.version,
                ResultCandidate.priority == result.priority,
            )
            .values(
                priority=result.priority - 1,
                version=ResultCandidate.version + 1,
                updated_at=deleted_at,
            )
            .execution_options(synchronize_session=False)
        ).rowcount
        if compacted != 1:
            db.rollback()
            raise ApiError(
                409,
                "PRIORITY_CONFLICT",
                "Priority đã thay đổi trong lúc xóa submission",
            )
        db.add(
            AuditLog(
                action="priority_compacted",
                entity_type="result_candidate",
                entity_id=result.id,
                actor=acting_name,
                old_value={
                    "priority": result.priority,
                    "arrival_seq": result.arrival_seq,
                    "version": result.version,
                },
                new_value={
                    "priority": result.priority - 1,
                    "arrival_seq": result.arrival_seq,
                },
            )
        )
    db.add(
        AuditLog(
            action="deleted",
            entity_type="result_candidate",
            entity_id=result_id,
            actor=acting_name,
            old_value={
                "priority": current.priority,
                "arrival_seq": current.arrival_seq,
                "version": expected_version,
            },
            new_value={"deleted_at": deleted_at.isoformat()},
        )
    )
    db.commit()
    db.expire_all()
    shifted_responses = [result_read(load_result(db, result.id)) for result in shifted]
    for response in shifted_responses:
        await hub.publish("updated", response.model_dump(mode="json"))
    await hub.publish(
        "deleted",
        {"id": result_id, "query_id": current.query_id, "arrival_seq": current.arrival_seq},
    )
    return Response(status_code=204)
