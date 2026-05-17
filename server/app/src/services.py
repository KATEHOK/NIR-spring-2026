import base64
import logging
from datetime import datetime
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.crypt import Password, JWT, SymmetricEncryption, Random
from src.utils import datetime_utcnow, timestamp_utcnow
from src.db_repository import AsyncAuthRepo as DBRepo
from src.redis_repository import AsyncAuthRepo as RedisRepo
from src.schemas import RefreshSchema, RegisterSchemas, LoginSchemas
from src.models import RefreshTokenModel, UserModel


logger = logging.getLogger(settings.LOGGER_NAME)


class SystemService:
    """Бизнес-логика служебных запросов"""

    @staticmethod
    async def get_hello():
        """Приветственное сообщение"""
        return {"msg": "Hello World!"}

    @staticmethod
    async def touch_db(session: AsyncSession):
        """Приветственное сообщение из БД"""
        return {"msg": await DBRepo.select_hello(session)}

    @staticmethod
    async def get_public_key():
        """Публичный ключ и алгоритм шифрования access-токена"""
        return {"algorithm": settings.JWT_ALGORITHM, "public_key": settings.JWT_PUBLIC_KEY}


class RegisterService:
    """Бизнес-логика регистрации пользователя"""

    @staticmethod
    async def issue_key(pin_code: str) -> tuple[str, bytes]:
        """Выпускает ключ пользователя, вернет key_part и зашифрованный ключ пользователя (на ключе приложения)"""
        key_part = Random.base32()
        key = f"{key_part}:{pin_code}".encode('utf-8')
        return key_part, SymmetricEncryption.encrypt(key)

    @staticmethod
    async def init(pin_code: str, password: str, redis: Redis) -> RegisterSchemas.Init.Resp:
        """Инициализация регистрации пользователя"""
        hashed_password = await Password.async_hash(password)
        key_part, encrypted_key = await RegisterService.issue_key(pin_code)
        session_id = Random.session_id()
        await RedisRepo.create_register_session(session_id, hashed_password, encrypted_key, redis)
        return RegisterSchemas.Init.Resp(session_id=session_id, key_part=key_part)

    @staticmethod
    async def accept(session_id: str, session: AsyncSession, redis: Redis) -> RegisterSchemas.Accept.Resp:
        """Подтверждение регистрации"""
        saved_data = await RedisRepo.get_register_session(session_id, redis)
        if saved_data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown session id (maybe expired)")
        await RedisRepo.delete_register_session(session_id, redis)
        user = await DBRepo.add_user(saved_data["password"], saved_data["key"], session)
        refresh_token = await TokenService.set_refresh_token(user.id, session=session)
        await session.commit()
        await RedisRepo.cache_refresh_token(
            token=refresh_token.token,
            token_id=refresh_token.id,
            user_id=refresh_token.user_id,
            revoked=refresh_token.revoked,
            expires_at=refresh_token.expires_at,
            redis=redis
        )
        return RegisterSchemas.Accept.Resp(
            refresh_token=refresh_token.token,
            access_token=JWT.issue_access_token(user.id, refresh_token.id),
        )


class LoginService:
    """Бизнес-логика входа пользователя"""

    @staticmethod
    async def issue_challenge(encrypted_user_key: bytes) -> tuple[bytes, bytes]:
        """
        Выпускает и зашифровывает challenge (вернет - (на ключе пользователя, на ключе приложения)):
        challenge = {challenge_random}:{timestamp_utcnow}
        """
        plain_challenge = f"{Random.urlsafe(16)}:{int(timestamp_utcnow())}".encode('utf-8')
        return (
            SymmetricEncryption.encrypt(plain_challenge, SymmetricEncryption.decrypt(encrypted_user_key)),
            SymmetricEncryption.encrypt(plain_challenge)
        )

    @staticmethod
    async def verify_otp(user: UserModel, encrypted_challenge: bytes, encrypted_otp: str) -> bool:
        """
        Проверяет OTP: otp = {challenge_random}:{login_count}
        """
        try:
            user_key = SymmetricEncryption.decrypt(user.key)
            otp = SymmetricEncryption.decrypt(base64.b64decode(encrypted_otp), user_key).decode('utf-8')
            if ":" not in otp:
                raise ValueError("Invalid OTP format")
            i = otp.index(":")
            login_count = otp[i+1:]
            if not login_count.isdigit():
                raise ValueError("Invalid login count")
            if int(login_count) != user.login_count:
                raise ValueError("Login count mismatch")
            challenge = SymmetricEncryption.decrypt(encrypted_challenge).decode('utf-8')
            if otp[:i] != challenge[:challenge.index(":")]:
                raise ValueError("Challenge mismatch")
            return True
        except (ValueError, Exception) as e:
            logger.info(f"Incorrect OTP for user_id={user.id}: {e}")
            return False

    @staticmethod
    async def init(user_id: int, password: str, session: AsyncSession, redis: Redis) -> LoginSchemas.Init.Resp:
        """Инициализирует вход пользователя"""
        user: UserModel = await DBRepo.select_user(user_id, session)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not await Password.async_verify(password, user.password):
            faults = await RedisRepo.incr_user_faults(user_id, redis)
            if faults >= settings.FAULTS_LIMIT:
                await RedisRepo.ban_user(user_id, redis)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
        if await RedisRepo.is_user_baned(user.id, redis):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Banned user")
        session_id = Random.session_id()
        user_challenge, app_challenge = await LoginService.issue_challenge(user.key)
        await RedisRepo.create_login_session(session_id, user_id, app_challenge, redis)
        return LoginSchemas.Init.Resp(
            session_id=session_id,
            challenge=base64.b64encode(user_challenge).decode('utf-8')
        )

    @staticmethod
    async def accept(session_id: str, otp: str, session: AsyncSession, redis: Redis) -> LoginSchemas.Accept.Resp:
        saved_data = await RedisRepo.get_login_session(session_id, redis)
        if saved_data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown session id (maybe expired)")
        await RedisRepo.delete_login_session(session_id, redis)
        user: UserModel = await DBRepo.select_user(saved_data["user_id"], session)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not await LoginService.verify_otp(user, saved_data["challenge"], otp):
            faults = await RedisRepo.incr_user_faults(user.id, redis)
            if faults >= settings.FAULTS_LIMIT:
                await RedisRepo.ban_user(user.id, redis)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Incorrect OTP")
        await RedisRepo.delete_user_faults(user.id, redis)
        refresh_token = await TokenService.set_refresh_token(user.id, session)
        await DBRepo.increment_user_login_count(user.id, session)
        await session.commit()
        await RedisRepo.cache_refresh_token(
            token=refresh_token.token,
            token_id=refresh_token.id,
            user_id=refresh_token.user_id,
            revoked=refresh_token.revoked,
            expires_at=refresh_token.expires_at,
            redis=redis
        )
        return LoginSchemas.Accept.Resp(
            refresh_token=refresh_token.token,
            access_token=JWT.issue_access_token(user.id, refresh_token.id),
        )


class TokenService:
    """Бизнес-логика работы с токенами"""

    @staticmethod
    async def validate_refresh(
            token: RefreshTokenModel | dict[str, int | str | bool | datetime] = None,
            require_not_expired: bool = False,
            require_not_revoked: bool = False,
    ):
        """Валидирует refresh-токен (выбрасывает HTTP-исключения)"""
        utcnow = datetime_utcnow()
        if token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        if isinstance(token, RefreshTokenModel):
            token = {
                "revoked": token.revoked,
                "expires_at": token.expires_at,
            }
        if require_not_expired and utcnow >= token["expires_at"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        if require_not_revoked and token["revoked"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    @staticmethod
    async def set_refresh_token(user_id: int, session: AsyncSession) -> RefreshTokenModel:
        """Выпускает и добавляет в БД новый refresh-токен, обрабатывая нарушение уникальности (не выполняет коммит)"""
        refresh_token, refresh_token_exp = JWT.issue_refresh_token()
        try:
            return await DBRepo.add_refresh_token(
                user_id=user_id,
                token=refresh_token,
                expires_at=refresh_token_exp,
                session=session
            )
        except IntegrityError:
            raise HTTPException(status_code=500, detail="Impossible! Failed to generate unique refresh token")

    @staticmethod
    async def refresh(refresh_token: str, session: AsyncSession, redis: Redis) -> RefreshSchema.Resp:
        """Обновление токенов (пока что только access)"""
        token = await RedisRepo.get_cached_refresh_token(refresh_token, redis)
        if token is None:
            token = await DBRepo.select_refresh_token(refresh_token, session)
            if token is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            token = {
                "token_id": token.id,
                "user_id": token.user_id,
                "revoked": token.revoked,
                "expires_at": token.expires_at,
            }
            await RedisRepo.cache_refresh_token(token=refresh_token, redis=redis, **token)
        await TokenService.validate_refresh(
            token=token,
            require_not_expired=True,
            require_not_revoked=True
        )
        return RefreshSchema.Resp(
            refresh_token=refresh_token,
            access_token=JWT.issue_access_token(token["user_id"], token["token_id"]),
        )

    @staticmethod
    async def logout(refresh_token: str, session: AsyncSession, redis: Redis) -> None:
        """Выход пользователя"""
        revoked_token_id = await DBRepo.revoke_refresh_token(refresh_token, session)
        if revoked_token_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown token")
        await session.commit()
        await RedisRepo.delete_cached_refresh_token(refresh_token, redis)
        await RedisRepo.add_refresh_token_to_blacklist(revoked_token_id, redis)
        return None
