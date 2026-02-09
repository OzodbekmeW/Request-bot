"""Telegram bot service — send OTP messages."""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


class TelegramService:
    async def send_otp_message(self, telegram_id: int, code: str) -> bool:
        text = (
            f"🔐 Tasdiqlash kodi: <b>{code}</b>\n\n"
            f"⏰ Kod 5 daqiqa amal qiladi.\n"
            f"⚠️ Bu kodni hech kimga bermang!"
        )
        return await self._send(telegram_id, text)

    async def send_login_notification(self, telegram_id: int, ip: str, ua: str) -> bool:
        text = (
            f"🔔 <b>Yangi kirish</b>\n\n📍 IP: {ip}\n📱 Qurilma: {ua[:50]}\n\n"
            f"Agar bu siz bo'lmasangiz, tezda parolingizni o'zgartiring!"
        )
        return await self._send(telegram_id, text)

    async def _send(self, chat_id: int, text: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{_API}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                )
                return r.status_code == 200
        except Exception as exc:
            logger.error("Telegram send failed: %s", exc)
            return False


telegram_service = TelegramService()


async def get_telegram_service() -> TelegramService:
    return telegram_service
