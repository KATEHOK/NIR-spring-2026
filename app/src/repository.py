from sqlalchemy import text
from src.database import async_session


class AsyncAuthRepo:

    @staticmethod
    async def select_hello():
        """Получение 'Hello World!' из БД"""
        async with async_session() as session:
            result = await session.execute(text("SELECT 'Hello World!'"))
            return result.scalar()


