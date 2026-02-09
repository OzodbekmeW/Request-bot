"""Admin management schemas."""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Parol kamida 8 ta belgidan iborat bo'lishi kerak")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Parolda kamida 1 ta katta harf bo'lishi kerak")
    if not re.search(r"[a-z]", v):
        raise ValueError("Parolda kamida 1 ta kichik harf bo'lishi kerak")
    if not re.search(r"\d", v):
        raise ValueError("Parolda kamida 1 ta raqam bo'lishi kerak")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        raise ValueError("Parolda kamida 1 ta maxsus belgi bo'lishi kerak")
    return v


class AdminCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    is_super_admin: bool = False
    permission_ids: list[UUID] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def check_pwd(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("username")
    @classmethod
    def check_uname(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username faqat harf, raqam va _ bo'lishi kerak")
        return v.lower()


class AdminUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    is_active: Optional[bool] = None
    is_super_admin: Optional[bool] = None

    @field_validator("password")
    @classmethod
    def check_pwd(cls, v: Optional[str]) -> Optional[str]:
        return _validate_password(v) if v else v


class AdminPermissionsUpdateRequest(BaseModel):
    permission_ids: list[UUID]


class AdminDetailResponse(BaseModel):
    id: UUID
    username: str
    email: str
    is_super_admin: bool
    is_active: bool
    permissions: list[dict]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class AdminListResponse(BaseModel):
    success: bool = True
    admins: list[AdminDetailResponse]
    total: int
    page: int
    limit: int


class AdminSingleResponse(BaseModel):
    success: bool = True
    admin: AdminDetailResponse


class AdminDeleteResponse(BaseModel):
    success: bool = True
    message: str
