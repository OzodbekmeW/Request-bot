"""Seed initial data — super admin + permissions."""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import hash_password
from app.models.admin import Admin
from app.models.permission import Permission

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

PERMISSIONS = [
    {"name": "can_view_admins", "resource": "admin", "action": "read", "description": "Adminlar ro'yxatini ko'rish"},
    {"name": "can_create_admin", "resource": "admin", "action": "create", "description": "Yangi admin yaratish"},
    {"name": "can_edit_admin", "resource": "admin", "action": "update", "description": "Admin ma'lumotlarini tahrirlash"},
    {"name": "can_delete_admin", "resource": "admin", "action": "delete", "description": "Adminni o'chirish"},
    {"name": "can_manage_permissions", "resource": "admin", "action": "manage", "description": "Ruxsatnomalarni boshqarish"},
    {"name": "can_view_users", "resource": "user", "action": "read", "description": "Foydalanuvchilarni ko'rish"},
    {"name": "can_edit_user", "resource": "user", "action": "update", "description": "Foydalanuvchini tahrirlash"},
    {"name": "can_delete_user", "resource": "user", "action": "delete", "description": "Foydalanuvchini o'chirish"},
    {"name": "can_deactivate_user", "resource": "user", "action": "deactivate", "description": "Bloklash/aktivlashtirish"},
]

SUPER_ADMIN = {
    "username": "superadmin",
    "email": "admin@example.com",
    "password": "SuperAdmin123!",
}


async def _create_permissions(db: AsyncSession) -> list[Permission]:
    result = []
    for p in PERMISSIONS:
        existing = (await db.execute(select(Permission).where(Permission.name == p["name"]))).scalar_one_or_none()
        if existing:
            result.append(existing)
            continue
        perm = Permission(**p)
        db.add(perm)
        result.append(perm)
        log.info("  + %s", p["name"])
    await db.flush()
    return result


async def _create_super_admin(db: AsyncSession, perms: list[Permission]) -> None:
    existing = (await db.execute(select(Admin).where(Admin.username == SUPER_ADMIN["username"]))).scalar_one_or_none()
    if existing:
        log.info("Super admin already exists")
        return
    admin = Admin(
        username=SUPER_ADMIN["username"],
        email=SUPER_ADMIN["email"],
        password_hash=hash_password(SUPER_ADMIN["password"]),
        is_super_admin=True,
        is_active=True,
        permissions=perms,
    )
    db.add(admin)
    log.info("Super admin created: %s / %s", SUPER_ADMIN["username"], SUPER_ADMIN["password"])


async def seed() -> None:
    log.info("=" * 50)
    log.info("Seeding database …")
    async with async_session_maker() as db:
        try:
            perms = await _create_permissions(db)
            await _create_super_admin(db, perms)
            await db.commit()
            log.info("✅ Done — %d permissions", len(perms))
        except Exception as e:
            await db.rollback()
            log.error("❌ %s", e)
            raise
    log.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed())
