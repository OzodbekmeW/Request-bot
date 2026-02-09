"""User management endpoints (admin-side)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import require_permission, verify_csrf_token
from app.models.admin import Admin
from app.models.admin_session import AdminSession
from app.schemas.user import (
    UserDeactivateResponse,
    UserDeleteResponse,
    UserDetailResponse,
    UserListResponse,
    UserSingleResponse,
    UserUpdateRequest,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/admin/users", tags=["User Management"])


def _user_detail(u) -> UserDetailResponse:
    return UserDetailResponse(
        id=u.id,
        phone_number=u.phone_number,
        telegram_id=int(u.telegram_id) if u.telegram_id else None,
        is_active=u.is_active,
        created_at=u.created_at,
        updated_at=u.updated_at,
        last_login=u.last_login,
    )


@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(require_permission("can_view_users")),
):
    users, total = await UserService(db).get_all(page, limit, search, is_active, sort_by, sort_order)
    return UserListResponse(users=[_user_detail(u) for u in users], total=total, page=page, limit=limit)


@router.get("/{user_id}", response_model=UserSingleResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(require_permission("can_view_users")),
):
    user = await UserService(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foydalanuvchi topilmadi")
    return UserSingleResponse(user=_user_detail(user))


@router.patch("/{user_id}", response_model=UserSingleResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple[Admin, AdminSession] = Depends(verify_csrf_token),
    __: Admin = Depends(require_permission("can_edit_user")),
):
    ok, err, user = await UserService(db).update(user_id, data.phone_number, data.telegram_id, data.is_active)
    if not ok:
        raise HTTPException(404 if "topilmadi" in err else 400, err)
    return UserSingleResponse(user=_user_detail(user))


@router.post("/{user_id}/deactivate", response_model=UserDeactivateResponse)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple[Admin, AdminSession] = Depends(verify_csrf_token),
    __: Admin = Depends(require_permission("can_deactivate_user")),
):
    ok, err, user = await UserService(db).deactivate(user_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, err)
    return UserDeactivateResponse(message="Foydalanuvchi bloklandi", user=_user_detail(user))


@router.post("/{user_id}/activate", response_model=UserDeactivateResponse)
async def activate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple[Admin, AdminSession] = Depends(verify_csrf_token),
    __: Admin = Depends(require_permission("can_deactivate_user")),
):
    ok, err, user = await UserService(db).activate(user_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, err)
    return UserDeactivateResponse(message="Foydalanuvchi aktivlashtirildi", user=_user_detail(user))


@router.delete("/{user_id}", response_model=UserDeleteResponse)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple[Admin, AdminSession] = Depends(verify_csrf_token),
    __: Admin = Depends(require_permission("can_delete_user")),
):
    ok, err = await UserService(db).delete(user_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, err)
    return UserDeleteResponse(message="Foydalanuvchi muvaffaqiyatli o'chirildi")
