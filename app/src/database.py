from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from src.config import settings


async_db_url = settings.ASYNC_DATABASE_URL
async_engine = create_async_engine(async_db_url)
async_session = async_sessionmaker(async_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    ...