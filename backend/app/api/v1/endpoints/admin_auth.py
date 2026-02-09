"""Admin auth endpoints — login / logout / me."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import RedisClient, get_redis
from app.dependencies.auth import get_client_ip, get_current_admin, get_user_agent
from app.models.admin import Admin
from app.models.admin_session import AdminSession
from app.schemas.auth import AdminLoginRequest, AdminLoginResponse, AdminLogoutResponse, AdminResponse
from app.services.admin_auth_service import AdminAuthService

router = APIRouter(prefix="/admin/auth", tags=["Admin Authentication"])


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    creds: AdminLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
    ip: str = Depends(get_client_ip),
    ua: str = Depends(get_user_agent),
):
    svc = AdminAuthService(db, redis)
    ok, err, admin, sess_tok, csrf = await svc.login(creds.username, creds.password, ip, ua)
    if not ok:
        code = 429 if "bloklangan" in (err or "").lower() else 401
        raise HTTPException(code, detail=err)

    response.set_cookie(
        key="admin_session",
        value=sess_tok,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        max_age=settings.ADMIN_SESSION_EXPIRATION_HOURS * 3600,
        path="/api/admin",
    )

    return AdminLoginResponse(
        success=True,
        admin=AdminResponse(
            id=admin.id,
            username=admin.username,
            email=admin.email,
            is_super_admin=admin.is_super_admin,
            is_active=admin.is_active,
            permissions=admin.permission_names(),
            created_at=admin.created_at,
        ),
        csrf_token=csrf,
    )


@router.post("/logout", response_model=AdminLogoutResponse)
async def admin_logout(
    response: Response,
    admin_data: tuple[Admin, AdminSession] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    _, session = admin_data
    svc = AdminAuthService(db, redis)
    await svc.logout(session.session_token)
    response.delete_cookie(key="admin_session", path="/api/admin")
    return AdminLogoutResponse(success=True, message="Muvaffaqiyatli chiqildi")


@router.get("/me", response_model=AdminResponse)
async def current_admin_info(
    admin_data: tuple[Admin, AdminSession] = Depends(get_current_admin),
):
    admin, _ = admin_data
    return AdminResponse(
        id=admin.id,
        username=admin.username,
        email=admin.email,
        is_super_admin=admin.is_super_admin,
        is_active=admin.is_active,
        permissions=admin.permission_names(),
        created_at=admin.created_at,
    )
