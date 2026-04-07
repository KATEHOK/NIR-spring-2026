from sqlalchemy import text, update, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import RefreshTokenModel


class AsyncAuthRepo:

    @staticmethod
    async def select_hello(session: AsyncSession):
        """Получение 'Hello World!' из БД"""
        result = await session.execute(text("SELECT 'Hello World!'"))
        return result.scalar()

    @staticmethod
    async def revoke_refresh_token(token: str, session: AsyncSession) -> bool:
        """Отзывает refresh-токен"""
        stmt = update(RefreshTokenModel).where(RefreshTokenModel.token == token).values(revoked=True)
        result = await session.execute(stmt)
        return result.rowcount > 0 # noqa

    @staticmethod
    async def select_refresh_token(token: str, session: AsyncSession) -> RefreshTokenModel | None:
        """Получает refresh-токен"""
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token == token)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


