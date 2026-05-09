import base64
import logging
from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.crypt import Password, JWT, SymmetricEncryption, Random
from src.utils import datetime_utcnow, timestamp_utcnow
from src.repository import AsyncAuthRepo
from src.schemas import RefreshSchema, RegisterSchemas, LoginSchemas
from src.models import RefreshTokenModel, UserModel


logger = logging.getLogger("auth_server")


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
    async def issue_key(pin_code: str) -> tuple[str, bytes]:
        """Выпускает ключ пользователя, вернет key_part и зашифрованный ключ пользователя (на ключе приложения)"""
        key_part = Random.base32()
        key = f"{key_part}:{pin_code}".encode('utf-8')
        return key_part, SymmetricEncryption.encrypt(key)

    @staticmethod
    async def init(pin_code: str, password: str, session: AsyncSession) -> RegisterSchemas.Init.Resp:
        """Инициализация регистрации пользователя"""
        hashed_password = await Password.async_hash(password)
        key_part, key = await RegisterService.issue_key(pin_code)
        user = await AsyncAuthRepo.add_user(hashed_password, key, session)
        token = await TokenService.set_refresh_token(user.id, accepted=False, fast=True, session=session)
        await session.commit()
        return RegisterSchemas.Init.Resp(refresh_token=token.token, key_part=key_part)

    @staticmethod
    async def accept(refresh_token: str, session: AsyncSession) -> RegisterSchemas.Accept.Resp:
        """Подтверждение регистрации"""
        old_token: RefreshTokenModel = await AsyncAuthRepo.select_refresh_token(refresh_token, session)
        await TokenService.validate_refresh(
            old_token,
            require_not_expired=True,
            require_not_accepted=True,
            require_not_revoked=True
        )
        old_token.revoked = True
        user: UserModel = await AsyncAuthRepo.select_user(old_token.user_id, session)
        await UserService.validate(user, require_not_active=True)
        user.is_active = True
        new_token = await TokenService.set_refresh_token(user.id, accepted=True, fast=False, session=session)
        await session.commit()
        return RegisterSchemas.Accept.Resp(
            refresh_token=new_token.token,
            access_token=JWT.issue_access_token(new_token.user_id, new_token.id),
        )


class LoginService:
    """Бизнес-логика входа пользователя"""

    @staticmethod
    async def issue_and_set_challenge(user: UserModel) -> bytes:
        """
        Выпускает challenge и вставляет его в БД (в зашифрованном на ключе приложения виде):
        challenge = {challenge_random}:{timestamp_utcnow}
        """
        plain_challenge = f"{Random.urlsafe(16)}:{int(timestamp_utcnow())}".encode('utf-8')
        user.challenge = SymmetricEncryption.encrypt(plain_challenge)
        plain_key = SymmetricEncryption.decrypt(user.key)
        return SymmetricEncryption.encrypt(plain_challenge, plain_key)

    @staticmethod
    async def verify_otp(user: UserModel, otp: bytes, session: AsyncSession):
        """
        Проверяет OTP (вызывает функцию, коммититящую и выбрасывающую HTTP-исключения):
        otp = {challenge_random}:{login_count}
        """
        try:
            key = SymmetricEncryption.decrypt(user.key)
            plain_otp = SymmetricEncryption.decrypt(otp, key).decode('utf-8')
            if ":" not in plain_otp:
                raise ValueError("Invalid OTP format")
            i = plain_otp.index(":")
            login_count = plain_otp[i+1:]
            if not login_count.isdigit():
                raise ValueError("Invalid login count")
            if int(login_count) != user.login_count:
                raise ValueError("Login count mismatch")
            challenge = SymmetricEncryption.decrypt(user.challenge).decode('utf-8')
            if plain_otp[:i] != challenge[:challenge.index(":")]:
                raise ValueError("Challenge mismatch")
        except (ValueError, Exception) as e:
            await LoginService.handle_incorrect_otp(user, str(e), session)

    @staticmethod
    async def handle_incorrect_otp(user: UserModel, detail: str, session: AsyncSession):
        """Обрабатывает ситуацию некорректного OTP (коммитит измененное число попыток)"""
        logger.info(f"Incorrect OTP for user_id={user.id}: {detail}")
        await AsyncAuthRepo.increment_user_faults(
            user_id=user.id,
            last_fault_at=datetime_utcnow(),
            challenge=None if user.failed_login_count + 1 >= settings.FAULT_LIMIT else user.challenge,
            session=session
        )
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Incorrect OTP")

    @staticmethod
    async def init(user_id: int, password: str, session: AsyncSession) -> LoginSchemas.Init.Resp:
        """Инициализирует вход пользователя"""
        user: UserModel = await AsyncAuthRepo.select_user(user_id, session)
        await UserService.validate(
            user,
            require_active=True,
            require_not_banned=True,
            session=session,
            password=password
        )
        challenge = await LoginService.issue_and_set_challenge(user)
        token = await TokenService.set_refresh_token(user.id, accepted=False, fast=True, session=session)
        await session.commit()
        return LoginSchemas.Init.Resp(
            refresh_token=token.token,
            challenge=base64.b64encode(challenge).decode('utf-8')
        )

    @staticmethod
    async def accept(refresh_token: str, otp: str, session: AsyncSession) -> LoginSchemas.Accept.Resp:
        old_token: RefreshTokenModel = await AsyncAuthRepo.select_refresh_token(refresh_token, session)
        await TokenService.validate_refresh(
            old_token,
            require_not_expired=True,
            require_not_accepted=True,
            require_not_revoked=True
        )
        user: UserModel = await AsyncAuthRepo.select_user(old_token.user_id, session)
        await UserService.validate(
            user,
            require_active=True,
            require_challenge=True,
            require_not_banned=True,
            session=session
        )
        await LoginService.verify_otp(user, base64.b64decode(otp), session)
        new_refresh = await TokenService.set_refresh_token(user.id, accepted=True, fast=False, session=session)
        new_access = JWT.issue_access_token(new_refresh.user_id, new_refresh.id)
        old_token.revoked = True
        await AsyncAuthRepo.update_user_successful_logged_in(user.id, session)
        await session.commit()
        return LoginSchemas.Accept.Resp(
            refresh_token=new_refresh.token,
            access_token=new_access,
        )


class UserService:
    """Бизнес-логика работы с пользователем"""

    @staticmethod
    async def is_banned(user: UserModel, session: AsyncSession = None) -> bool:
        """Проверяет: в бане ли пользователь, при необходимости сбрасывает счетчик ошибок"""
        if user.last_fault_at is None:
            return False
        fault_update_exp = user.last_fault_at + timedelta(minutes=settings.FAULT_LIMIT_UPDATE_PERIOD)
        ban_exp = user.last_fault_at + timedelta(minutes=settings.BAN_PERIOD)
        utcnow = datetime_utcnow()
        too_much_fault = user.failed_login_count >= settings.FAULT_LIMIT
        if (
            not too_much_fault and utcnow > fault_update_exp or
            too_much_fault and utcnow > ban_exp
        ):
            if session is None:
                raise RuntimeError("Session required for update login faults in ban check")
            user.failed_login_count = 0
            await session.commit()
            return False
        return too_much_fault

    @staticmethod
    async def validate(
            user: UserModel = None,
            require_active: bool = False,
            require_not_active: bool = False,
            require_challenge: bool = False,
            require_not_banned: bool = False,
            session: AsyncSession = None,
            password: str | None = None,
    ):
        """Валидирует пользователя (выбрасывает HTTP-исключения"""
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if password is not None and not await Password.async_verify(password, user.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
        if require_not_banned and await UserService.is_banned(user, session):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Banned user")
        if require_active and not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
        if require_not_active and user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active user")
        if require_challenge and user.challenge is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Challenge not set")


class TokenService:
    """Бизнес-логика работы с токенами"""

    @staticmethod
    async def validate_refresh(
            token: RefreshTokenModel = None,
            require_expired: bool = False,
            require_not_expired: bool = False,
            require_accepted: bool = False,
            require_not_accepted: bool = False,
            require_revoked: bool = False,
            require_not_revoked: bool = False,
    ):
        """Валидирует refresh-токен (выбрасывает HTTP-исключения)"""
        utcnow = datetime_utcnow()
        if token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        if require_expired and utcnow < token.expires_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token not expired")
        if require_not_expired and utcnow >= token.expires_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        if require_revoked and not token.revoked:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token not revoked")
        if require_not_revoked and token.revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token already revoked")
        if require_accepted and not token.accepted:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not accepted")
        if require_not_accepted and token.accepted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token already accepted")

    @staticmethod
    async def set_refresh_token(user_id: int, accepted: bool, fast: bool, session: AsyncSession) -> RefreshTokenModel:
        """Выпускает и добавляет в БД новый refresh-токен, обрабатывая нарушение уникальности (не выполняет коммит)"""
        refresh_token, refresh_token_exp = JWT.issue_refresh_token(fast)
        try:
            new_token = await AsyncAuthRepo.add_refresh_token(
                user_id=user_id,
                token=refresh_token,
                accepted=accepted,
                expires_at=refresh_token_exp,
                session=session
            )
            return new_token
        except IntegrityError:
            raise HTTPException(status_code=500, detail="Impossible! Failed to generate unique refresh token")

    @staticmethod
    async def refresh(refresh_token: str, session: AsyncSession) -> RefreshSchema.Resp:
        """Обновление токенов (пока что только access)"""
        token: RefreshTokenModel = await AsyncAuthRepo.select_refresh_token(refresh_token, session)
        await TokenService.validate_refresh(
            token=token,
            require_not_expired=True,
            require_accepted=True,
            require_not_revoked=True
        )
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

