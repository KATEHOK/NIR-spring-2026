from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.crypt import Password, JWT, SymmetricEncryption, Random
from src.repository import AsyncAuthRepo
from src.schemas import RefreshSchema, RegisterSchemas, LoginSchemas
from src.models import RefreshTokenModel


class SystemService:
    """Бизнес-логика служебных запросов"""

    @staticmethod
    async def get_hello():
        """Приветственное сообщение"""
        return {"msg": "Hello World!"}

    @staticmethod
    async def touch_db(session: AsyncSession):
        """Приветственное сообщение из БД"""
        return {"msg": await AsyncAuthRepo.select_hello(session)}

    @staticmethod
    async def get_public_key():
        """Публичный ключ и алгоритм шифрования access-токена"""
        return {"algorithm": settings.JWT_ALGORITHM, "public_key": settings.JWT_PUBLIC_KEY}


class RegisterService:
    """Бизнес-логика регистрации пользователя"""

    @staticmethod
    async def init(pin_code: str, password: str, session: AsyncSession) -> RegisterSchemas.Init.Resp:
        """Инициализация регистрации пользователя"""
        hashed_password = Password.hash(password)
        key_part = Random.base32()
        key = key_part + ":" + pin_code
        key_cipher = SymmetricEncryption.encrypt(key.encode('utf-8'))
        user = await AsyncAuthRepo.add_user(hashed_password, key_cipher, session)
        refresh_token, refresh_token_exp = JWT.issue_refresh_token(fast=True)
        await AsyncAuthRepo.add_refresh_token(
            user.id,
            refresh_token,
            False,
            refresh_token_exp,
            session
        )
        await session.commit()
        return RegisterSchemas.Init.Resp(refresh_token=refresh_token, key_part=key_part)

    @staticmethod
    async def accept(refresh_token: str, session: AsyncSession) -> RegisterSchemas.Accept.Resp:
        """Подтверждение регистрации"""
        old_token = await TokenService.get_refresh_token(refresh_token, False, session)
        if old_token.accepted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token already accepted")
        old_token.revoked = True
        user = await AsyncAuthRepo.select_user(old_token.user_id, session)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user.is_active = True
        refresh_token, refresh_token_exp = JWT.issue_refresh_token()
        new_token = await AsyncAuthRepo.add_refresh_token(
            user.id,
            refresh_token,
            True,
            refresh_token_exp,
            session
        )
        await session.commit()
        return RegisterSchemas.Accept.Resp(
            refresh_token=new_token.token,
            access_token=JWT.issue_access_token(new_token.user_id, new_token.id),
        )


class LoginService:
    """Бизнес-логика входа пользователя"""

    @staticmethod
    async def init(user_id: int, password: str, session: AsyncSession) -> LoginSchemas.Init.Resp: ...

    @staticmethod
    async def accept(refresh_token: str, otp: str, session: AsyncSession) -> LoginSchemas.Accept.Resp: ...


class TokenService:
    """Бизнес-логика работы с токенами"""

    @staticmethod
    async def get_refresh_token(refresh_token: str, accepted: bool, session: AsyncSession) -> RefreshTokenModel:
        """Получает токен из БД (выбрасывает HTTP-исключения, accepted = True - требует подтвержденный токен)"""
        token = await AsyncAuthRepo.select_refresh_token(refresh_token, session)
        if token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        if token.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        if token.revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
        if accepted and not token.accepted:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not accepted")
        return token

    @staticmethod
    async def refresh(refresh_token: str, session: AsyncSession) -> RefreshSchema.Resp:
        """Обновление токенов (пока что только access)"""
        token = await TokenService.get_refresh_token(refresh_token, True, session)
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

