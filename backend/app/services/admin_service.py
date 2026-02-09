"""Admin CRUD service."""

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.admin import Admin
from app.models.permission import Permission


class AdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all(self, page: int = 1, limit: int = 20) -> tuple[list[Admin], int]:
        total = (await self.db.execute(select(func.count()).select_from(Admin))).scalar() or 0
        stmt = (
            select(Admin)
            .options(selectinload(Admin.permissions))
            .order_by(Admin.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        admins = list((await self.db.execute(stmt)).scalars().all())
        return admins, total

    async def get_by_id(self, aid: UUID) -> Optional[Admin]:
        stmt = select(Admin).options(selectinload(Admin.permissions)).where(Admin.id == aid)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_username(self, name: str) -> Optional[Admin]:
        return (await self.db.execute(select(Admin).where(Admin.username == name))).scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Admin]:
        return (await self.db.execute(select(Admin).where(Admin.email == email))).scalar_one_or_none()

    async def create(
        self,
        username: str,
        email: str,
        password: str,
        is_super_admin: bool = False,
        permission_ids: list[UUID] | None = None,
    ) -> tuple[bool, Optional[str], Optional[Admin]]:
        if await self.get_by_username(username):
            return False, "Bu foydalanuvchi nomi band", None
        if await self.get_by_email(email):
            return False, "Bu email manzili band", None

        perms: list[Permission] = []
        if permission_ids:
            perms = list((await self.db.execute(select(Permission).where(Permission.id.in_(permission_ids)))).scalars().all())
            if len(perms) != len(permission_ids):
                return False, "Ba'zi ruxsatnomalar topilmadi", None

        admin = Admin(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_super_admin=is_super_admin,
            permissions=perms,
        )
        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)
        return True, None, admin

    async def update(
        self,
        aid: UUID,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_super_admin: Optional[bool] = None,
    ) -> tuple[bool, Optional[str], Optional[Admin]]:
        admin = await self.get_by_id(aid)
        if not admin:
            return False, "Admin topilmadi", None

        if username and username != admin.username:
            if await self.get_by_username(username):
                return False, "Bu foydalanuvchi nomi band", None
            admin.username = username

        if email and email != admin.email:
            if await self.get_by_email(email):
                return False, "Bu email manzili band", None
            admin.email = email

        if password:
            admin.password_hash = hash_password(password)
        if is_active is not None:
            admin.is_active = is_active
        if is_super_admin is not None:
            admin.is_super_admin = is_super_admin

        await self.db.commit()
        await self.db.refresh(admin)
        return True, None, admin

    async def update_permissions(
        self, aid: UUID, perm_ids: list[UUID]
    ) -> tuple[bool, Optional[str], Optional[Admin]]:
        admin = await self.get_by_id(aid)
        if not admin:
            return False, "Admin topilmadi", None

        perms = list((await self.db.execute(select(Permission).where(Permission.id.in_(perm_ids)))).scalars().all())
        if len(perms) != len(perm_ids):
            return False, "Ba'zi ruxsatnomalar topilmadi", None

        admin.permissions = perms
        await self.db.commit()
        await self.db.refresh(admin)
        return True, None, admin

    async def delete(self, aid: UUID, current_id: UUID) -> tuple[bool, Optional[str]]:
        if aid == current_id:
            return False, "O'zingizni o'chira olmaysiz"
        admin = await self.get_by_id(aid)
        if not admin:
            return False, "Admin topilmadi"
        if admin.is_super_admin:
            return False, "Super adminni o'chirib bo'lmaydi"
        await self.db.delete(admin)
        await self.db.commit()
        return True, None

    async def all_permissions(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.resource, Permission.action)
        return list((await self.db.execute(stmt)).scalars().all())
