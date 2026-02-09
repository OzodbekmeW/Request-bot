"""User auth endpoints — OTP send / verify / refresh."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import RedisClient, get_redis
from app.dependencies.auth import get_client_ip
from app.schemas.auth import (
    RefreshTokenRequest,
    RefreshTokenResponse,
    SendOTPRequest,
    SendOTPResponse,
    UserResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.services.telegram_service import TelegramService, get_telegram_service
from app.services.user_auth_service import UserAuthService

router = APIRouter(prefix="/auth", tags=["User Authentication"])


@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(
    body: SendOTPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
    tg: TelegramService = Depends(get_telegram_service),
    ip: str = Depends(get_client_ip),
):
    svc = UserAuthService(db, redis, tg)
    ok, err, retry = await svc.send_otp(body.phone_number, ip, body.telegram_chat_id)
    if not ok:
        code = 429 if ("limit" in err.lower() or "daqiqa" in err.lower()) else 400
        raise HTTPException(code, detail=err)
    return SendOTPResponse(success=True, message="Kod yuborildi", retry_after=retry)


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(
    body: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
    tg: TelegramService = Depends(get_telegram_service),
):
    svc = UserAuthService(db, redis, tg)
    ok, err, user, access, refresh = await svc.verify_otp(body.phone_number, body.code)
    if not ok:
        code = 403 if "bloklangan" in err.lower() else 400
        raise HTTPException(code, detail=err)
    return VerifyOTPResponse(
        success=True,
        user=UserResponse(id=user.id, phone_number=user.phone_number),
        access_token=access,
        refresh_token=refresh,
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
    tg: TelegramService = Depends(get_telegram_service),
):
    svc = UserAuthService(db, redis, tg)
    ok, err, new_access, new_refresh = await svc.refresh_tokens(body.refresh_token)
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=err)
    return RefreshTokenResponse(success=True, access_token=new_access, refresh_token=new_refresh)
