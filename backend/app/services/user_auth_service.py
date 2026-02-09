"""User authentication service — OTP verify, token issue & refresh."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import RedisClient
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.otp_service import OTPService
from app.services.telegram_service import TelegramService


class UserAuthService:
    def __init__(self, db: AsyncSession, redis: RedisClient, telegram: TelegramService) -> None:
        self.db = db
        self.redis = redis
        self.telegram = telegram
        self.otp = OTPService(db, redis)

    # Send OTP 
    async def send_otp(
        self, phone: str, ip: str, telegram_chat_id: Optional[int] = None
    ) -> tuple[bool, Optional[str], int]:
        allowed, err, retry = await self.otp.check_rate_limit(phone, ip)
        if not allowed:
            return False, err, retry

        user = (await self.db.execute(select(User).where(User.phone_number == phone))).scalar_one_or_none()
        if user and not user.is_active:
            return False, "Foydalanuvchi bloklangan. Administrator bilan bog'laning", 0

        # Agar telegram_chat_id berilgan bo'lsa va user bazada bo'lsa — yangilash
        if user and telegram_chat_id and not user.telegram_id:
            user.telegram_id = telegram_chat_id

        otp = await self.otp.create_otp(phone, ip)
        await self.db.commit()

        # OTP ni Telegram ga yuborish
        tg_id = (user.telegram_id if user else None) or telegram_chat_id
        if tg_id:
            await self.telegram.send_otp_message(int(tg_id), otp.code)

        await self.otp.bump_rate_limit(phone, ip)
        retry = await self.otp.get_retry_after(phone)
        return True, None, max(retry, 60)

    # Verify OTP 
    async def verify_otp(
        self, phone: str, code: str
    ) -> tuple[bool, Optional[str], Optional[User], Optional[str], Optional[str]]:
        ok, err, _ = await self.otp.verify_otp(phone, code)
        if not ok:
            await self.db.commit()
            return False, err, None, None, None

        user = (await self.db.execute(select(User).where(User.phone_number == phone))).scalar_one_or_none()
        if not user:
            user = User(phone_number=phone)
            self.db.add(user)
            await self.db.flush()

        if not user.is_active:
            await self.db.commit()
            return False, "Foydalanuvchi bloklangan", None, None, None

        user.last_login = datetime.now(timezone.utc)

        access = create_access_token({"sub": str(user.id), "phone": user.phone_number})
        refresh = create_refresh_token({"sub": str(user.id)})

        self.db.add(RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS),
        ))
        await self.db.commit()
        return True, None, user, access, refresh

    # Refresh 
    async def refresh_tokens(
        self, raw_token: str
    ) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
        payload = decode_refresh_token(raw_token)
        if not payload:
            return False, "Noto'g'ri yoki muddati tugagan token", None, None

        uid = payload.get("sub")
        if not uid:
            return False, "Noto'g'ri token", None, None

        stored = (
            await self.db.execute(
                select(RefreshToken)
                .where(RefreshToken.token_hash == hash_token(raw_token), RefreshToken.is_revoked == False)  # noqa: E712
            )
        ).scalar_one_or_none()

        if not stored or not stored.is_valid():
            return False, "Token topilmadi yoki muddati tugagan", None, None

        user = (await self.db.execute(select(User).where(User.id == UUID(uid)))).scalar_one_or_none()
        if not user or not user.is_active:
            return False, "Foydalanuvchi topilmadi yoki bloklangan", None, None

        stored.is_revoked = True

        new_access = create_access_token({"sub": str(user.id), "phone": user.phone_number})
        new_refresh = create_refresh_token({"sub": str(user.id)})

        self.db.add(RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS),
        ))
        await self.db.commit()
        return True, None, new_access, new_refresh
