"""User CRUD service (admin-side management)."""

from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import User


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[User], int]:
        q = select(User)
        cq = select(func.count()).select_from(User)

        if search:
            f = or_(User.phone_number.ilike(f"%{search}%"))
            q = q.where(f)
            cq = cq.where(f)

        if is_active is not None:
            q = q.where(User.is_active == is_active)
            cq = cq.where(User.is_active == is_active)

        total = (await self.db.execute(cq)).scalar() or 0

        col = getattr(User, sort_by, User.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        q = q.offset((page - 1) * limit).limit(limit)

        users = list((await self.db.execute(q)).scalars().all())
        return users, total

    async def get_by_id(self, uid: UUID) -> Optional[User]:
        return (await self.db.execute(select(User).where(User.id == uid))).scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        return (await self.db.execute(select(User).where(User.phone_number == phone))).scalar_one_or_none()

    async def update(
        self,
        uid: UUID,
        phone_number: Optional[str] = None,
        telegram_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[bool, Optional[str], Optional[User]]:
        user = await self.get_by_id(uid)
        if not user:
            return False, "Foydalanuvchi topilmadi", None

        if phone_number and phone_number != user.phone_number:
            if await self.get_by_phone(phone_number):
                return False, "Bu telefon raqami band", None
            user.phone_number = phone_number

        if telegram_id is not None:
            user.telegram_id = telegram_id
        if is_active is not None:
            user.is_active = is_active

        await self.db.commit()
        await self.db.refresh(user)
        return True, None, user

    async def deactivate(self, uid: UUID) -> tuple[bool, Optional[str], Optional[User]]:
        user = await self.get_by_id(uid)
        if not user:
            return False, "Foydalanuvchi topilmadi", None

        user.is_active = False
        tokens = (await self.db.execute(select(RefreshToken).where(RefreshToken.user_id == uid))).scalars().all()
        for t in tokens:
            t.is_revoked = True

        await self.db.commit()
        await self.db.refresh(user)
        return True, None, user

    async def activate(self, uid: UUID) -> tuple[bool, Optional[str], Optional[User]]:
        user = await self.get_by_id(uid)
        if not user:
            return False, "Foydalanuvchi topilmadi", None
        user.is_active = True
        await self.db.commit()
        await self.db.refresh(user)
        return True, None, user

    async def delete(self, uid: UUID) -> tuple[bool, Optional[str]]:
        user = await self.get_by_id(uid)
        if not user:
            return False, "Foydalanuvchi topilmadi"
        await self.db.delete(user)
        await self.db.commit()
        return True, None
