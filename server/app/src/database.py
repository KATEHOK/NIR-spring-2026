from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from src.config import settings


async_db_url = settings.ASYNC_DATABASE_URL
async_engine = create_async_engine(
    async_db_url,
    pool_size=50,        # базовое число соединений
    max_overflow=150,    # ещё до 150 при пике
    pool_pre_ping=True,  # проверять соединение перед использованием
    pool_recycle=3600,   # пересоздавать соединения старше часа
)
async_session = async_sessionmaker(async_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    ...