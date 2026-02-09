"""Auth dependencies — user JWT guard, admin session guard, CSRF, RBAC."""

from typing import Optional
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import RedisClient, get_redis
from app.core.security import decode_access_token
from app.models.admin import Admin
from app.models.admin_session import AdminSession
from app.models.user import User
from app.services.admin_auth_service import AdminAuthService

bearer_scheme = HTTPBearer(auto_error=False)


# Helpers 

async def get_client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def get_user_agent(request: Request) -> str:
    return request.headers.get("User-Agent", "unknown")


# User guard 

async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token taqdim etilmagan")

    payload = decode_access_token(creds.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Noto'g'ri yoki muddati tugagan token")

    user = (await db.execute(select(User).where(User.id == UUID(payload["sub"])))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Foydalanuvchi topilmadi")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Foydalanuvchi bloklangan")
    return user


# Admin guard

async def get_admin_session_token(
    admin_session: Optional[str] = Cookie(None, alias="admin_session"),
) -> str:
    if not admin_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessiya topilmadi. Tizimga kiring")
    return admin_session


async def get_current_admin(
    token: str = Depends(get_admin_session_token),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
) -> tuple[Admin, AdminSession]:
    svc = AdminAuthService(db, redis)
    ok, admin, session = await svc.validate_session(token)
    if not ok or not admin or not session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessiya yaroqsiz yoki muddati tugagan")
    return admin, session


async def verify_csrf_token(
    request: Request,
    admin_data: tuple[Admin, AdminSession] = Depends(get_current_admin),
    x_csrf_token: Optional[str] = Header(None),
) -> tuple[Admin, AdminSession]:
    admin, session = admin_data
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return admin, session
    if not x_csrf_token or session.csrf_token != x_csrf_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF token noto'g'ri yoki taqdim etilmagan")
    return admin, session


# Permission check 

def require_permission(name: str):
    async def _check(
        admin_data: tuple[Admin, AdminSession] = Depends(verify_csrf_token),
    ) -> Admin:
        admin, _ = admin_data
        if not admin.has_permission(name):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"'{name}' ruxsati kerak")
        return admin

    return _check


def require_super_admin():
    async def _check(
        admin_data: tuple[Admin, AdminSession] = Depends(verify_csrf_token),
    ) -> Admin:
        admin, _ = admin_data
        if not admin.is_super_admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Faqat super admin uchun")
        return admin

    return _check
