"""Application Configuration — loaded from .env"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Database 
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = ""
    DATABASE_NAME: str = "secure_backend"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # JWT 
    JWT_ACCESS_SECRET: str = Field(default="change-this-secret-key-in-production-min-32-chars", min_length=32)
    JWT_REFRESH_SECRET: str = Field(default="change-this-refresh-secret-in-production-min-32", min_length=32)
    JWT_ACCESS_EXPIRATION_MINUTES: int = 15
    JWT_REFRESH_EXPIRATION_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # Admin Session 
    ADMIN_SESSION_SECRET: str = Field(default="admin-session-secret-key-min-32-characters-long", min_length=32)
    ADMIN_SESSION_EXPIRATION_HOURS: int = 24

    # Telegram 
    TELEGRAM_BOT_TOKEN: str = "your-telegram-bot-token"

    # Security 
    CSRF_SECRET: str = Field(default="csrf-secret-key-min-32-characters-long", min_length=32)
    FRONTEND_URL: str = "http://localhost:3001"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # Rate Limiting 
    OTP_LIMIT_MINUTE: int = 1
    OTP_LIMIT_HOUR: int = 3
    OTP_LIMIT_DAY_PER_IP: int = 10
    LOGIN_LIMIT_ATTEMPTS: int = 5
    LOGIN_BLOCK_DURATION_SECONDS: int = 900

    # Server 
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Computed URLs 
    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        pwd = f":{self.DATABASE_PASSWORD}" if self.DATABASE_PASSWORD else ""
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}{pwd}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @computed_field
    @property
    def DATABASE_URL_SYNC(self) -> str:
        pwd = f":{self.DATABASE_PASSWORD}" if self.DATABASE_PASSWORD else ""
        return (
            f"postgresql+psycopg2://{self.DATABASE_USER}{pwd}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
