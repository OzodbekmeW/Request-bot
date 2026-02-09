"""User management schemas."""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class UserDetailResponse(BaseModel):
    id: UUID
    phone_number: str
    telegram_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    success: bool = True
    users: list[UserDetailResponse]
    total: int
    page: int
    limit: int


class UserSingleResponse(BaseModel):
    success: bool = True
    user: UserDetailResponse


class UserUpdateRequest(BaseModel):
    phone_number: Optional[str] = Field(None, min_length=9, max_length=20)
    telegram_id: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("phone_number")
    @classmethod
    def clean_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        v = re.sub(r"[\s\-]", "", v)
        if not re.match(r"^\+?[1-9]\d{8,14}$", v):
            raise ValueError("Noto'g'ri telefon raqam formati")
        return v


class UserDeactivateResponse(BaseModel):
    success: bool = True
    message: str
    user: UserDetailResponse


class UserDeleteResponse(BaseModel):
    success: bool = True
    message: str
