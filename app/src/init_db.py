import asyncio
import src.models
from src.database import async_engine, Base


async def init():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(init())
