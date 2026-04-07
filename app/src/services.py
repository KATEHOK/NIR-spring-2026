from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.crypt import JWT
from src.repository import AsyncAuthRepo
from src.schemas import RefreshSchema, RegisterSchemas, LoginSchemas


class SystemService:
    """Бизнес-логика служебных запросов"""

    @staticmethod
    async def get_hello():
        return {"msg": "Hello World!"}

    @staticmethod
    async def touch_db(session: AsyncSession):
        return {"msg": await AsyncAuthRepo.select_hello(session)}

    @staticmethod
    async def get_public_key():
        return {"algorithm": settings.JWT_ALGORITHM, "public_key": settings.JWT_PUBLIC_KEY}


class RegisterService:
    """Бизнес-логика регистрации пользователя"""

    @staticmethod
    async def init(pin_code: str, password: str, session: AsyncSession) -> RegisterSchemas.Init.Resp: ...

    @staticmethod
    async def accept(refresh_token: str, session: AsyncSession) -> RegisterSchemas.Accept.Resp: ...


class LoginService:
    """Бизнес-логика входа пользователя"""

    @staticmethod
    async def init(user_id: int, password: str, session: AsyncSession) -> LoginSchemas.Init.Resp: ...

    @staticmethod
    async def accept(refresh_token: str, otp: str, session: AsyncSession) -> LoginSchemas.Accept.Resp: ...


class TokenService:
    """Бизнес-логика работы с токенами"""

    @staticmethod
    async def refresh(refresh_token: str, session: AsyncSession) -> RefreshSchema.Resp:
        """Обновление токенов (пока что только access)"""
        token = await AsyncAuthRepo.select_refresh_token(refresh_token, session)
        if token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        if token.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        if token.revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
        if not token.is_accepted:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not accepted")
        return RefreshSchema.Resp(
            refresh_token=token.token,
            access_token=JWT.issue_access_token(token.user_id, token.id),
        )

    @staticmethod
    async def logout(refresh_token: str, session: AsyncSession) -> None:
        """Выход пользователя"""
        await AsyncAuthRepo.revoke_refresh_token(refresh_token, session)
        await session.commit()
        return None

