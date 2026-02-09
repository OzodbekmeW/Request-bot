"""Async Redis client wrapper for rate-limiting & caching."""

from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings


class RedisClient:
    def __init__(self) -> None:
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()

    @property
    def client(self) -> aioredis.Redis:
        if not self._client:
            raise RuntimeError("Redis not connected")
        return self._client

    # helpers
    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        await self.client.set(key, value, ex=ex)

    async def setex(self, key: str, seconds: int, value: str) -> None:
        await self.client.setex(key, seconds, value)

    async def incr(self, key: str) -> int:
        return await self.client.incr(key)

    async def expire(self, key: str, seconds: int) -> None:
        await self.client.expire(key, seconds)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return (await self.client.exists(key)) > 0

    async def ttl(self, key: str) -> int:
        return await self.client.ttl(key)

    async def incr_with_ttl(self, key: str, ttl: int) -> int:
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        results = await pipe.execute()
        return results[0]


redis_client = RedisClient()


async def get_redis() -> RedisClient:
    return redis_client
