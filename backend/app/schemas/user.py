"""User-related Pydantic schemas (Users CRUD)."""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import PaginationMeta


class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    manager = "manager"
    viewer = "viewer"


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    role: UserRole


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    role: UserRole | None = None
    password: str | None = Field(default=None, min_length=8)
    is_active: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    role: UserRole
    is_active: bool
    theme: str
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    data: list[UserRead]
    meta: PaginationMeta
