"""Security utilities — hashing, JWT, OTP, tokens."""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


# Password 
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# Tokens 
def generate_otp_code(length: int = 6) -> str:
    lo, hi = 10 ** (length - 1), 10**length - 1
    return str(secrets.randbelow(hi - lo) + lo)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# JWT 
def _jwt_encode(data: dict, secret: str, token_type: str, delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {**data, "exp": now + delta, "iat": now, "type": token_type}
    return jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    delta = expires_delta or timedelta(minutes=settings.JWT_ACCESS_EXPIRATION_MINUTES)
    return _jwt_encode(data, settings.JWT_ACCESS_SECRET, "access", delta)


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    delta = expires_delta or timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)
    return _jwt_encode(data, settings.JWT_REFRESH_SECRET, "refresh", delta)


def _jwt_decode(token: str, secret: str, expected_type: str) -> dict | None:
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None


def decode_access_token(token: str) -> dict | None:
    return _jwt_decode(token, settings.JWT_ACCESS_SECRET, "access")


def decode_refresh_token(token: str) -> dict | None:
    return _jwt_decode(token, settings.JWT_REFRESH_SECRET, "refresh")
