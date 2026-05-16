from datetime import datetime
from redis.asyncio import Redis
from src.config import settings


class AsyncAuthRepo:
    access_token_expire_seconds: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    session_expire_seconds: int = settings.SESSION_EXPIRE_MINUTES * 60
    faults_update_period_seconds: int = settings.FAULTS_UPDATE_PERIOD_MINUTES * 60
    ban_period_seconds: int = settings.BAN_PERIOD_MINUTES * 60
    cache_expire_seconds: int = settings.REDIS_CACHE_EXPIRE_MINUTES * 60

    blacklist_prefix = "blacklist"
    register_prefix = "register"
    login_prefix = "login"
    faults_prefix = "faults"
    banlist_prefix = "banlist"
    cache_prefix = "cache"
    cache_refresh_token_prefix = f"{cache_prefix}:rt"

    @classmethod
    async def add_refresh_token_to_blacklist(cls, token_id: int, redis: Redis) -> None:
        await redis.setex(f"{cls.blacklist_prefix}:{token_id}", cls.access_token_expire_seconds, "1")

    @classmethod
    async def is_refresh_token_blacklisted(cls, token_id: int, redis: Redis) -> bool:
        return await redis.exists(f"{cls.blacklist_prefix}:{token_id}")

    @classmethod
    async def create_register_session(
            cls,
            session_id: str,
            hashed_password: bytes,
            encrypted_key: bytes,
            redis: Redis
    ) -> None:
        key = f"{cls.register_prefix}:{session_id}"
        async with redis.pipeline(transaction=True) as pipe:
            await pipe.hset(key, mapping={
                "password": hashed_password,
                "key": encrypted_key
            })
            await pipe.expire(key, cls.session_expire_seconds)
            await pipe.execute()

    @classmethod
    async def get_register_session(cls, session_id: str, redis: Redis) -> dict[str, bytes] | None:
        data = await redis.hgetall(f"{cls.register_prefix}:{session_id}")
        if not data:
            return None
        return {
            "password": data[b"password"],
            "key": data[b"key"]
        }

    @classmethod
    async def delete_register_session(cls, session_id: str, redis: Redis) -> None:
        await redis.delete(f"{cls.register_prefix}:{session_id}")

    @classmethod
    async def create_login_session(cls, session_id: str, user_id: int, challenge: bytes, redis: Redis) -> None:
        key = f"{cls.login_prefix}:{session_id}"
        async with redis.pipeline(transaction=True) as pipe:
            await pipe.hset(key, mapping={
                "user_id": str(user_id),
                "challenge": challenge,
            })
            await pipe.expire(key, cls.session_expire_seconds)
            await pipe.execute()

    @classmethod
    async def get_login_session(cls, session_id: str, redis: Redis) -> dict[str, int | bytes] | None:
        data = await redis.hgetall(f"{cls.login_prefix}:{session_id}")
        if not data:
            return None
        return {
            "user_id": int(data[b"user_id"]),
            "challenge": data[b"challenge"]
        }

    @classmethod
    async def delete_login_session(cls, session_id: str, redis: Redis) -> None:
        await redis.delete(f"{cls.login_prefix}:{session_id}")

    @classmethod
    async def cache_refresh_token(
            cls,
            token: str,
            token_id: int,
            user_id: int,
            revoked: bool,
            expires_at: datetime,
            redis: Redis
    ) -> None:
        key = f"{cls.cache_refresh_token_prefix}:{token}"
        async with redis.pipeline(transaction=True) as pipe:
            await pipe.hset(key, mapping={
                "token_id": str(token_id),
                "user_id": str(user_id),
                "revoked": b"1" if revoked else b"0",
                "expires_at": expires_at.isoformat(),
            })
            await pipe.expire(key, cls.cache_expire_seconds)
            await pipe.execute()

    @classmethod
    async def get_cached_refresh_token(cls, token: str, redis: Redis) -> dict[str, int | bool | datetime] | None:
        data = await redis.hgetall(f"{cls.cache_refresh_token_prefix}:{token}")
        if not data:
            return None
        return {
            "token_id": int(data[b"token_id"]),
            "user_id": int(data[b"user_id"]),
            "revoked": data[b"revoked"] == b"1",
            "expires_at": datetime.fromisoformat(data[b"expires_at"].decode()),
        }

    @classmethod
    async def delete_cached_refresh_token(cls, token: str, redis: Redis) -> None:
        await redis.delete(f"{cls.cache_refresh_token_prefix}:{token}")

    @classmethod
    async def incr_user_faults(cls, user_id: int, redis: Redis) -> int:
        key = f"{cls.faults_prefix}:{user_id}"
        async with redis.pipeline(transaction=True) as pipe:
            await pipe.incr(key)
            await pipe.expire(key, cls.faults_update_period_seconds)
            result = await pipe.execute()
        return int(result[0])

    @classmethod
    async def delete_user_faults(cls, user_id: int, redis: Redis) -> None:
        await redis.delete(f"{cls.faults_prefix}:{user_id}")

    @classmethod
    async def ban_user(cls, user_id: int, redis: Redis) -> None:
        await redis.setex(f"{cls.banlist_prefix}:{user_id}", cls.ban_period_seconds, "1")

    @classmethod
    async def is_user_baned(cls, user_id: int, redis: Redis) -> bool:
        return b"1" == await redis.get(f"{cls.banlist_prefix}:{user_id}")

