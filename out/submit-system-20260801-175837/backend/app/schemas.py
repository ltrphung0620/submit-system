from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class AuthSessionRead(BaseModel):
    authenticated: bool
    client_type: Literal["anonymous", "salamanders", "ui"]
    actor: str | None


class ResultCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "file_name": "query-p1-1-kis",
                    "query_content": "Tìm khoảnh khắc một người bước vào cửa hàng.",
                    "img_id": 24834,
                    "video_id": "L21_V001",
                    "submitter": "Định",
                },
                {
                    "file_name": "query-p1-2-qa",
                    "query_content": "Địa danh xuất hiện trong hình thuộc tỉnh nào?",
                    "img_id": 24834,
                    "video_id": "L21_V001",
                    "answer": "Bình Định",
                    "submitter": "Định",
                },
                {
                    "file_name": "query-p1-3-trake",
                    "query_content": "Theo dõi chiếc xe màu đỏ qua các khung hình.",
                    "img_id": [24834, 25230, 25432],
                    "video_id": "L21_V001",
                    "submitter": "Định",
                },
            ]
        },
    )

    file_name: StrictStr = Field(
        description="Tên file query không có đuôi .txt; hậu tố -kis, -qa hoặc -trake xác định loại."
    )
    query_content: StrictStr = Field(description="Nội dung mô tả của query.")
    img_id: StrictInt | list[StrictInt] = Field(
        description="Một frame ID cho KIS/QA; mảng frame ID có thứ tự cho TRAKE."
    )
    video_id: StrictStr
    submitter: StrictStr
    answer: StrictStr | None = Field(
        default=None, description="Bắt buộc với QA và không được gửi với KIS/TRAKE."
    )
    note: StrictStr | None = None
    image_base64: StrictStr | None = Field(
        default=None,
        description="Ảnh JPEG, PNG hoặc WebP dưới dạng base64 thuần hoặc data URL.",
    )
    image_mime_type: StrictStr | None = None


class ResultPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(strict=True, ge=1)
    img_id: StrictInt | list[StrictInt] | None = None
    video_id: StrictStr | None = None
    answer: StrictStr | None = None
    note: StrictStr | None = None


class PrioritySwap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_result_id: StrictStr
    second_result_id: StrictStr
    expected_first_version: int = Field(strict=True, ge=1)
    expected_second_version: int = Field(strict=True, ge=1)


class PriorityReorder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: StrictStr
    ordered_result_ids: list[StrictStr] = Field(min_length=2)
    expected_versions: dict[StrictStr, StrictInt]


class ResultRead(BaseModel):
    id: str
    query_id: str
    file_name: str
    query_type: str
    arrival_seq: int
    priority: int
    video_id: str
    img_id: int | list[int]
    answer: str | None
    submitter: str
    note: str | None
    created_at: datetime
    updated_at: datetime
    version: int
    structural_validation_status: str
    official_validation_status: str
    image_url: str | None
    image_mime_type: str | None


class QueryRead(BaseModel):
    id: str
    query_set_id: str
    file_name: str
    query_type: str
    content: str
    display_order: int
    source_path: str
    results: list[ResultRead] = []


class QuerySetRead(BaseModel):
    id: str
    name: str
    original_zip_name: str
    is_active: bool
    created_at: datetime
    created_by: str
    import_status: str
    query_count: int
