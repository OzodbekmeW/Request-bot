"""
Telegram Bot — httpx bilan ishlaydi (qo'shimcha kutubxona kerak emas).

Foydalanuvchilarga /start, /help, /myid buyruqlarini beradi.
OTP kodini backend API o'zi yuboradi (TelegramService orqali).

Ishga tushirish:
    cd backend
    python -m bot.main
"""

import asyncio
import logging
import sys
import re
from pathlib import Path

import httpx

# backend papkasini path'ga qo'shish
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.core.config import settings

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("bot")

API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
TIMEOUT = httpx.Timeout(30, connect=10)
BACKEND_URL = f"http://localhost:{settings.PORT}"  # Backend API manzili


# Telegram API helpers

async def send_message(client: httpx.AsyncClient, chat_id: int, text: str) -> bool:
    try:
        r = await client.post(
            f"{API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        )
        return r.status_code == 200
    except Exception as e:
        log.error("sendMessage xato: %s", e)
        return False


async def get_updates(client: httpx.AsyncClient, offset: int) -> list[dict]:
    try:
        r = await client.post(
            f"{API}/getUpdates",
            json={"offset": offset, "timeout": 25, "allowed_updates": ["message"]},
            timeout=httpx.Timeout(35, connect=10),
        )
        if r.status_code == 200:
            return r.json().get("result", [])
    except httpx.ReadTimeout:
        pass
    except Exception as e:
        log.error("getUpdates xato: %s", e)
        await asyncio.sleep(3)
    return []


# ── Command handlers ────────────────────────────────────────────────────────

async def handle_start(client: httpx.AsyncClient, msg: dict) -> None:
    chat_id = msg["chat"]["id"]
    first_name = msg.get("from", {}).get("first_name", "Foydalanuvchi")
    username = msg.get("from", {}).get("username", "?")

    text = (
        f"👋 Assalomu alaykum, <b>{first_name}</b>!\n\n"
        f"📱 Sizning Telegram ID: <code>{chat_id}</code>\n\n"
        f"🔐 <b>OTP kod olish uchun:</b>\n"
        f"Telefon raqamingizni yuboring (masalan: +998901234567)\n\n"
        f"Kod darhol shu botga keladi! ⚡️\n\n"
        f"<b>Boshqa buyruqlar:</b>\n"
        f"/myid — Telegram ID nusxalash\n"
        f"/help — Yordam"
    )
    await send_message(client, chat_id, text)
    log.info("/start — user=@%s id=%s", username, chat_id)


async def handle_myid(client: httpx.AsyncClient, msg: dict) -> None:
    chat_id = msg["chat"]["id"]
    text = (
        f"🆔 <b>Sizning Telegram ID:</b>\n\n"
        f"<code>{chat_id}</code>\n\n"
        f"☝️ Ustiga bosib nusxalang va tizimda ishlating."
    )
    await send_message(client, chat_id, text)


async def handle_help(client: httpx.AsyncClient, msg: dict) -> None:
    chat_id = msg["chat"]["id"]
    text = (
        "📖 <b>Yordam</b>\n\n"
        "Bu bot orqali siz:\n"
        "• Tizimga kirish uchun OTP kod olasiz\n"
        "• Xavfsizlik xabarnomalarini olasiz\n\n"
        "<b>Qanday ishlaydi?</b>\n"
        "1. /start bosing → Telegram ID oling\n"
        "2. Telefon raqamingizni yuboring (masalan: +998901234567)\n"
        "3. OTP kod darhol shu botga keladi ⚡️\n"
        "4. Kodni kiritib tizimga kiring\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start — Boshlash\n"
        "/myid — Telegram ID\n"
        "/help — Shu yordam"
    )
    await send_message(client, chat_id, text)


def validate_phone_number(phone: str) -> str | None:
    """Telefon raqamni tekshiradi va formatlaydi.
    
    Qabul qilinadigan formatlar:
    - +998901234567
    - 998901234567
    - 901234567
    - +998 90 123 45 67
    - 90 123 45 67
    
    Returns:
        str: Formatlangan raqam (masalan: +998901234567)
        None: Noto'g'ri format
    """
    # Barcha bo'sh joylar, tire va qavs belgilarini o'chirish
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    
    # + bilan boshlansa
    if cleaned.startswith('+998') and len(cleaned) == 13:
        return cleaned
    
    # 998 bilan boshlansa
    if cleaned.startswith('998') and len(cleaned) == 12:
        return f'+{cleaned}'
    
    # 9 bilan boshlansa (90, 91, 93, 94, 95, 97, 98, 99, 33, 88)
    if len(cleaned) == 9 and cleaned[0] == '9':
        return f'+998{cleaned}'
    
    return None


async def request_otp(client: httpx.AsyncClient, phone: str, chat_id: int) -> dict:
    """Backend API ga OTP so'rovi yuboradi."""
    try:
        response = await client.post(
            f"{BACKEND_URL}/api/auth/send-otp",
            json={
                "phone_number": phone,
                "telegram_chat_id": chat_id
            },
            timeout=httpx.Timeout(10)
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        log.error("Backend API xato: %s", e)
        return {"success": False, "error": str(e)}


async def handle_phone_number(client: httpx.AsyncClient, msg: dict) -> None:
    """Telefon raqamni qabul qilib OTP yuboradi."""
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    
    # Telefon raqamni validatsiya qilish
    phone = validate_phone_number(text)
    
    if not phone:
        await send_message(
            client, chat_id,
            "❌ Telefon raqam noto'g'ri!\n\n"
            "Iltimos, to'g'ri formatda kiriting:\n"
            "• <code>+998901234567</code>\n"
            "• <code>998901234567</code>\n"
            "• <code>901234567</code>\n"
            "• <code>+998 90 123 45 67</code>\n\n"
            "Qaytadan urinib ko'ring 👇"
        )
        return
    
    # Loading xabari
    await send_message(
        client, chat_id,
        f"📱 Telefon: <code>{phone}</code>\n\n"
        f"⏳ OTP kod yuborilmoqda..."
    )
    
    # Backend'dan OTP so'rash
    result = await request_otp(client, phone, chat_id)
    
    if result["success"]:
        await send_message(
            client, chat_id,
            f"✅ <b>OTP kod yuborildi!</b>\n\n"
            f"📱 Telefon: <code>{phone}</code>\n"
            f"🔐 Kod: <code>{result['data'].get('otp_code', 'XXXXXX')}</code>\n\n"
            f"⏰ Amal qilish muddati: 5 daqiqa\n\n"
            f"💡 Kodni tizimga kiritib login qiling!"
        )
        log.info("✅ OTP yuborildi: phone=%s chat_id=%s", phone, chat_id)
    else:
        await send_message(
            client, chat_id,
            f"❌ <b>Xatolik yuz berdi!</b>\n\n"
            f"OTP kodni yuborib bo'lmadi.\n"
            f"Iltimos, qaytadan urinib ko'ring.\n\n"
            f"<code>{result['error']}</code>"
        )
        log.error("❌ OTP xato: phone=%s error=%s", phone, result.get("error"))


async def handle_unknown(client: httpx.AsyncClient, msg: dict) -> None:
    chat_id = msg["chat"]["id"]
    await send_message(
        client, chat_id,
        "❓ Bu xabarni tushunolmadim.\n\n"
        "📱 Telefon raqam yuboring (masalan: +998901234567)\n"
        "Yoki buyruqlardan foydalaning:\n\n"
        "/start — Boshlash\n"
        "/myid — Telegram ID\n"
        "/help — Yordam"
    )


COMMANDS = {
    "/start": handle_start,
    "/myid": handle_myid,
    "/help": handle_help,
}


async def process_update(client: httpx.AsyncClient, update: dict) -> None:
    msg = update.get("message")
    if not msg:
        return

    text = (msg.get("text") or "").strip()
    
    # Buyruqmi?
    if text.startswith("/"):
        cmd = text.split()[0].split("@")[0].lower()
        handler = COMMANDS.get(cmd, handle_unknown)
        await handler(client, msg)
    else:
        # Oddiy xabar - telefon raqam bo'lishi mumkin
        await handle_phone_number(client, msg)


# Asosiy loop 

async def polling_loop() -> None:
    offset = 0

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Bot ma'lumotlarini tekshirish
        try:
            r = await client.get(f"{API}/getMe")
            if r.status_code == 200:
                me = r.json().get("result", {})
                log.info(
                    "🤖 Bot ishga tushdi: @%s (%s)",
                    me.get("username", "?"), me.get("first_name", "?"),
                )
            else:
                log.error("❌ Bot token noto'g'ri! Status: %s", r.status_code)
                log.error("   .env fayldagi TELEGRAM_BOT_TOKEN ni tekshiring.")
                return
        except Exception as e:
            log.error("❌ Telegram API'ga ulanib bo'lmadi: %s", e)
            return

        log.info("📡 Polling boshlandi... (Ctrl+C bilan to'xtatish)")

        while True:
            updates = await get_updates(client, offset)
            for upd in updates:
                offset = upd["update_id"] + 1
                try:
                    await process_update(client, upd)
                except Exception as e:
                    log.error("Update #%s xato: %s", upd.get("update_id"), e)


def main() -> None:
    log.info("🚀 Bot ishga tushmoqda...")

    if settings.TELEGRAM_BOT_TOKEN in ("your-telegram-bot-token", ""):
        log.error("❌ TELEGRAM_BOT_TOKEN .env da sozlanmagan!")
        log.error("   @BotFather dan token oling va .env ga yozing.")
        log.error("")
        log.error("   Qadamlar:")
        log.error("   1. Telegram'da @BotFather ga /newbot yozing")
        log.error("   2. Bot nomini kiriting")
        log.error("   3. Berilgan tokenni .env faylga yozing:")
        log.error("      TELEGRAM_BOT_TOKEN=1234567890:ABCdef...")
        sys.exit(1)

    try:
        asyncio.run(polling_loop())
    except KeyboardInterrupt:
        log.info("👋 Bot to'xtatildi.")


if __name__ == "__main__":
    main()
