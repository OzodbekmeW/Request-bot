"""Admin management endpoints — CRUD admins & permissions."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import require_permission, verify_csrf_token
from app.models.admin import Admin
from app.models.admin_session import AdminSession
from app.schemas.admin import (
    AdminCreateRequest,
    AdminDeleteResponse,
    AdminDetailResponse,
    AdminListResponse,
    AdminPermissionsUpdateRequest,
    AdminSingleResponse,
    AdminUpdateRequest,
)
from app.schemas.auth import PermissionResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin/admins", tags=["Admin Management"])


def _admin_detail(a: Admin) -> AdminDetailResponse:
    return AdminDetailResponse(
        id=a.id,
        username=a.username,
        email=a.email,
        is_super_admin=a.is_super_admin,
        is_active=a.is_active,
        permissions=[{"id": str(p.id), "name": p.name, "resource": p.resource, "action": p.action} for p in a.permissions],
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


#  List 

@router.get("/", response_model=AdminListResponse)
async def list_admins(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(require_permission("can_view_admins")),
):
    svc = AdminService(db)
    admins, total = await svc.get_all(page, limit)
    return AdminListResponse(admins=[_admin_detail(a) for a in admins], total=total, page=page, limit=limit)


#  Permissions list 

@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(require_permission("can_view_admins")),
):
    perms = await AdminService(db).all_permissions()
    return [PermissionResponse(id=p.id, name=p.name, description=p.description, resource=p.resource, action=p.action) for p in perms]


#Get one 

@router.get("/{admin_id}", response_model=AdminSingleResponse)
async def get_admin(
    admin_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(require_permission("can_view_admins")),
):
    admin = await AdminService(db).get_by_id(admin_id)
    if not admin:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Admin topilmadi")
    return AdminSingleResponse(admin=_admin_detail(admin))


# Create 

@router.post("/", response_model=AdminSingleResponse, status_code=201)
async def create_admin(
    data: AdminCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(require_permission("can_create_admin")),
):
    ok, err, admin = await AdminService(db).create(
        username=data.username,
        email=data.email,
        password=data.password,
        is_super_admin=data.is_super_admin,
        permission_ids=data.permission_ids,
    )
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, err)
    return AdminSingleResponse(admin=_admin_detail(admin))


# Update

@router.patch("/{admin_id}", response_model=AdminSingleResponse)
async def update_admin(
    admin_id: UUID,
    data: AdminUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple[Admin, AdminSession] = Depends(verify_csrf_token),
    __: Admin = Depends(require_permission("can_edit_admin")),
):
    me, _ = admin_data
    if admin_id == me.id and data.is_active is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "O'zingizni deactivate qila olmaysiz")

    ok, err, admin = await AdminService(db).update(
        admin_id, data.username, data.email, data.password, data.is_active, data.is_super_admin
    )
    if not ok:
        raise HTTPException(404 if "topilmadi" in err else 400, err)
    return AdminSingleResponse(admin=_admin_detail(admin))


# Permissions update 

@router.put("/{admin_id}/permissions", response_model=AdminSingleResponse)
async def update_permissions(
    admin_id: UUID,
    data: AdminPermissionsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(require_permission("can_manage_permissions")),
):
    svc = AdminService(db)
    target = await svc.get_by_id(admin_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Admin topilmadi")
    if target.is_super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Super admin ruxsatnomalari o'zgartirilmaydi")

    ok, err, admin = await svc.update_permissions(admin_id, data.permission_ids)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, err)
    return AdminSingleResponse(admin=_admin_detail(admin))


# Delete 

@router.delete("/{admin_id}", response_model=AdminDeleteResponse)
async def delete_admin(
    admin_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple[Admin, AdminSession] = Depends(verify_csrf_token),
    __: Admin = Depends(require_permission("can_delete_admin")),
):
    me, _ = admin_data
    ok, err = await AdminService(db).delete(admin_id, me.id)
    if not ok:
        code = 404 if "topilmadi" in err else 403 if ("Super" in err or "O'zingiz" in err) else 400
        raise HTTPException(code, err)
    return AdminDeleteResponse(message="Admin muvaffaqiyatli o'chirildi")
