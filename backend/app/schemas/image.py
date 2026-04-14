"""Product image Pydantic schemas."""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImageSource(str, enum.Enum):
    upload = "upload"
    ai = "ai"
    import_ = "import"


class ImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    is_primary: bool
    source: ImageSource
    sort_order: int
    created_at: datetime


class ImageUpdate(BaseModel):
    is_primary: bool | None = None
    sort_order: int | None = None


class ImageListResponse(BaseModel):
    data: list[ImageRead]
