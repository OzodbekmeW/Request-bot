"""Authentication schemas (user + admin)."""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# User Auth 

class SendOTPRequest(BaseModel):
    phone_number: str = Field(..., min_length=9, max_length=20, examples=["+998901234567"])
    telegram_chat_id: Optional[int] = Field(None, examples=[123456789], description="Telegram bot /start dan olingan ID")

    @field_validator("phone_number")
    @classmethod
    def clean_phone(cls, v: str) -> str:
        v = re.sub(r"[\s\-]", "", v)
        if not re.match(r"^\+?[1-9]\d{8,14}$", v):
            raise ValueError("Noto'g'ri telefon raqam formati. +998XXXXXXXXX")
        return v


class SendOTPResponse(BaseModel):
    success: bool
    message: str
    retry_after: int


class VerifyOTPRequest(BaseModel):
    phone_number: str = Field(..., min_length=9, max_length=20)
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Kod faqat raqamlardan iborat bo'lishi kerak")
        return v

    @field_validator("phone_number")
    @classmethod
    def clean_phone(cls, v: str) -> str:
        v = re.sub(r"[\s\-]", "", v)
        if not re.match(r"^\+?[1-9]\d{8,14}$", v):
            raise ValueError("Noto'g'ri telefon raqam formati")
        return v


class UserResponse(BaseModel):
    id: UUID
    phone_number: str
    model_config = {"from_attributes": True}


class VerifyOTPResponse(BaseModel):
    success: bool
    user: UserResponse
    access_token: str
    refresh_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class RefreshTokenResponse(BaseModel):
    success: bool
    access_token: str
    refresh_token: str


# Admin Auth 

class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)


class PermissionResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    resource: str
    action: str
    model_config = {"from_attributes": True}


class AdminResponse(BaseModel):
    id: UUID
    username: str
    email: str
    is_super_admin: bool
    is_active: bool
    permissions: list[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class AdminLoginResponse(BaseModel):
    success: bool
    admin: AdminResponse
    csrf_token: str


class AdminLogoutResponse(BaseModel):
    success: bool
    message: str


# Errors 

class ErrorResponse(BaseModel):
    success: bool = False
    detail: str
