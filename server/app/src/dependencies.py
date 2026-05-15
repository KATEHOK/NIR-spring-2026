import jwt
from typing import AsyncGenerator
from redis.asyncio import Redis
from fastapi import status, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import async_session
from src.crypt import JWT
from src.redis_client import get_redis_client
from src.redis_repository import AsyncAuthRepo as RedisRepo


security = HTTPBearer(description="Enter your access token", scheme_name="AccessToken")


async def get_redis() -> AsyncGenerator[Redis, None]:
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def validate_rid_and_get_sub_from_security_header(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        redis: Redis = Depends(get_redis),
) -> int:
    try:
        payload = JWT.decode(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        sub = payload.get("sub")
        rid = payload.get("rid")
        if sub is None or rid is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        if await RedisRepo.is_refresh_token_blacklisted(int(rid), redis):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
        return int(sub)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

