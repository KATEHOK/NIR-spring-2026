from redis.asyncio import Redis
from src.config import settings


class AsyncAuthRepo:
    access_token_expire_seconds: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    blacklist_prefix = "blacklist"

    @classmethod
    async def add_refresh_token_to_blacklist(cls, token_id: int, redis: Redis) -> None:
        await redis.setex(f"{cls.blacklist_prefix}:{token_id}", cls.access_token_expire_seconds, "1")

    @classmethod
    async def is_refresh_token_blacklisted(cls, token_id: int, redis: Redis) -> bool:
        return await redis.exists(f"{cls.blacklist_prefix}:{token_id}")


