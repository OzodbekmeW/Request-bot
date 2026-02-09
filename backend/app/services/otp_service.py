"""OTP service — create, verify, rate-limit."""

from typing import Optional

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import RedisClient
from app.core.security import generate_otp_code
from app.models.otp_code import OTPCode


class OTPService:
    def __init__(self, db: AsyncSession, redis: RedisClient) -> None:
        self.db = db
        self.redis = redis

    # Rate limiting 
    async def check_rate_limit(
        self, phone: str, ip: str
    ) -> tuple[bool, Optional[str], int]:
        """Returns (allowed, error_msg, retry_after_sec)."""
        mk = f"otp:phone:{phone}:minute"
        hk = f"otp:phone:{phone}:hour"
        ik = f"otp:ip:{ip}:day"

        mc = await self.redis.get(mk)
        if mc and int(mc) >= settings.OTP_LIMIT_MINUTE:
            ttl = max(await self.redis.ttl(mk), 1)
            return False, "1 daqiqada faqat 1 marta OTP yuborishingiz mumkin", ttl

        hc = await self.redis.get(hk)
        if hc and int(hc) >= settings.OTP_LIMIT_HOUR:
            ttl = max(await self.redis.ttl(hk), 1)
            return False, "1 soatda maksimum 3 marta OTP yuborishingiz mumkin", ttl

        ic = await self.redis.get(ik)
        if ic and int(ic) >= settings.OTP_LIMIT_DAY_PER_IP:
            ttl = max(await self.redis.ttl(ik), 1)
            return False, "Kunlik limit tugadi. Ertaga qaytadan urinib ko'ring", ttl

        return True, None, 0

    async def bump_rate_limit(self, phone: str, ip: str) -> None:
        await self.redis.incr_with_ttl(f"otp:phone:{phone}:minute", 60)
        await self.redis.incr_with_ttl(f"otp:phone:{phone}:hour", 3600)
        await self.redis.incr_with_ttl(f"otp:ip:{ip}:day", 86400)

    async def get_retry_after(self, phone: str) -> int:
        return max(await self.redis.ttl(f"otp:phone:{phone}:minute"), 0)

    # ── CRUD ────────────────────────────────────────────────────────────────
    async def _deactivate_old(self, phone: str) -> None:
        stmt = (
            update(OTPCode)
            .where(OTPCode.phone_number == phone, OTPCode.is_used == False)  # noqa: E712
            .values(is_used=True)
        )
        await self.db.execute(stmt)

    async def create_otp(self, phone: str, ip: str) -> OTPCode:
        await self._deactivate_old(phone)
        code = generate_otp_code()
        otp = OTPCode(
            phone_number=phone,
            code=code,
            expires_at=func.now() + text("interval '5 minutes'"),
            ip_address=ip,
        )
        self.db.add(otp)
        await self.db.flush()
        return otp

    async def verify_otp(
        self, phone: str, code: str
    ) -> tuple[bool, Optional[str], Optional[OTPCode]]:
        """Returns (valid, error_msg, otp)."""
        stmt = (
            select(OTPCode)
            .where(
                OTPCode.phone_number == phone,
                OTPCode.is_used == False,  # noqa: E712
                OTPCode.expires_at > func.now(),
            )
            .order_by(OTPCode.created_at.desc())
            .limit(1)
        )
        otp = (await self.db.execute(stmt)).scalar_one_or_none()

        if not otp:
            return False, "Tasdiqlash kodi topilmadi yoki muddati tugagan. Yangi kod so'rang", None

        if otp.attempts >= 3:
            otp.is_used = True
            await self.db.flush()
            return False, "Urinishlar soni tugadi. Yangi kod so'rang", None

        if otp.code != code:
            otp.attempts += 1
            await self.db.flush()
            left = 3 - otp.attempts
            if left > 0:
                return False, f"Noto'g'ri kod. {left} ta urinish qoldi", None
            otp.is_used = True
            await self.db.flush()
            return False, "Urinishlar soni tugadi. Yangi kod so'rang", None

        otp.is_used = True
        await self.db.flush()
        return True, None, otp
