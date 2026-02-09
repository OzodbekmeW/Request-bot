"""Admin authentication service — login, logout, session validation."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.redis import RedisClient
from app.core.security import generate_csrf_token, generate_session_token, verify_password
from app.models.admin import Admin
from app.models.admin_session import AdminSession


class AdminAuthService:
    def __init__(self, db: AsyncSession, redis: RedisClient) -> None:
        self.db = db
        self.redis = redis

    # Rate limiting 
    async def check_login_rate(self, username: str) -> tuple[bool, Optional[str], int]:
        bk = f"admin:block:{username}"
        blocked = await self.redis.get(bk)
        if blocked:
            ttl = await self.redis.ttl(bk)
            return False, f"Hisobingiz vaqtincha bloklangan. {ttl} soniyadan keyin qaytadan urinib ko'ring", ttl
        return True, None, 0

    async def _bump_fail(self, username: str) -> int:
        ak = f"admin:attempts:{username}"
        count = await self.redis.incr_with_ttl(ak, settings.LOGIN_BLOCK_DURATION_SECONDS)
        if count >= settings.LOGIN_LIMIT_ATTEMPTS:
            await self.redis.setex(f"admin:block:{username}", settings.LOGIN_BLOCK_DURATION_SECONDS, "1")
        return count

    async def _clear_fails(self, username: str) -> None:
        await self.redis.delete(f"admin:attempts:{username}")

    # Login 
    async def login(
        self, username: str, password: str, ip: str, ua: str
    ) -> tuple[bool, Optional[str], Optional[Admin], Optional[str], Optional[str]]:
        ok, err, _ = await self.check_login_rate(username)
        if not ok:
            return False, err, None, None, None

        stmt = (
            select(Admin)
            .options(selectinload(Admin.permissions))
            .where((Admin.username == username) | (Admin.email == username))
        )
        admin = (await self.db.execute(stmt)).scalar_one_or_none()
        generic = "Noto'g'ri foydalanuvchi nomi yoki parol"

        if not admin:
            await self._bump_fail(username)
            return False, generic, None, None, None

        if not admin.is_active:
            return False, "Hisobingiz bloklangan. Administrator bilan bog'laning", None, None, None

        if not verify_password(password, admin.password_hash):
            cnt = await self._bump_fail(username)
            left = settings.LOGIN_LIMIT_ATTEMPTS - cnt
            if left > 0:
                return False, f"{generic}. {left} ta urinish qoldi", None, None, None
            return False, "Hisobingiz vaqtincha bloklangan", None, None, None

        await self._clear_fails(username)

        session_token = generate_session_token()
        csrf_token = generate_csrf_token()
        session = AdminSession(
            admin_id=admin.id,
            session_token=session_token,
            csrf_token=csrf_token,
            ip_address=ip,
            user_agent=ua,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.ADMIN_SESSION_EXPIRATION_HOURS),
        )
        self.db.add(session)
        await self.db.commit()
        return True, None, admin, session_token, csrf_token

    # Logout 
    async def logout(self, token: str) -> bool:
        r = await self.db.execute(delete(AdminSession).where(AdminSession.session_token == token))
        await self.db.commit()
        return r.rowcount > 0

    # Session validation 
    async def validate_session(
        self, token: str
    ) -> tuple[bool, Optional[Admin], Optional[AdminSession]]:
        stmt = (
            select(AdminSession)
            .options(selectinload(AdminSession.admin).selectinload(Admin.permissions))
            .where(AdminSession.session_token == token)
        )
        session = (await self.db.execute(stmt)).scalar_one_or_none()
        if not session:
            return False, None, None
        if session.is_expired():
            await self.db.delete(session)
            await self.db.commit()
            return False, None, None
        if not session.admin.is_active:
            return False, None, None
        return True, session.admin, session

    # Cleanup 
    async def cleanup_expired(self) -> int:
        r = await self.db.execute(delete(AdminSession).where(AdminSession.expires_at < func.now()))
        await self.db.commit()
        return r.rowcount
