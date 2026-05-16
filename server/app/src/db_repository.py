from datetime import datetime
from sqlalchemy import text, update, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import RefreshTokenModel, UserModel


class AsyncAuthRepo:

    @staticmethod
    async def select_hello(session: AsyncSession):
        """Получение 'Hello World!' из БД"""
        result = await session.execute(text("SELECT 'Hello World!'"))
        return result.scalar()

    @staticmethod
    async def revoke_refresh_token(token: str, session: AsyncSession) -> int | None:
        """Отзывает refresh-токен"""
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token == token)
            .values(revoked=True)
            .returning(RefreshTokenModel.id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def select_user(user_id: int, session: AsyncSession) -> UserModel | None:
        """Получает пользователя по id"""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def select_refresh_token(token: str, session: AsyncSession) -> RefreshTokenModel | None:
        """Получает refresh-токен по значению"""
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token == token)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def add_user(password: bytes, key: bytes, session: AsyncSession) -> UserModel:
        """Создает неактивного пользователя (выполняет flush)"""
        user = UserModel(password=password, key=key)
        session.add(user)
        await session.flush([user])
        return user

    @staticmethod
    async def add_refresh_token(
            user_id: int,
            token: str,
            expires_at: datetime,
            session: AsyncSession
    ) -> RefreshTokenModel:
        """Создает refresh-токен (выполняет flush)"""
        refresh_token = RefreshTokenModel(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )
        session.add(refresh_token)
        await session.flush([refresh_token])
        return refresh_token

    @staticmethod
    async def increment_user_login_count(user_id: int, session: AsyncSession) -> None:
        """Инкриминирует счетчик успеха"""
        await session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(login_count=UserModel.login_count + 1)
        )
        return None

