"""Auth-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    role: str
    is_active: bool
    theme: str
    created_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class MeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    theme: Literal["light", "dark"] | None = None
    password: str | None = Field(default=None, min_length=8)
    current_password: str | None = None

    @model_validator(mode="after")
    def _password_requires_current(self) -> MeUpdate:
        if self.password is not None and not self.current_password:
            raise ValueError("current_password is required when changing password")
        return self
