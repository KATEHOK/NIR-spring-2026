import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.router import auth_router
from src.redis_client import redis_pool, get_redis_client


logger = logging.getLogger(settings.LOGGER_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = get_redis_client()
    try:
        await client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis not available – {e}")
    yield
    await redis_pool.disconnect(inuse_connections=True)
    logger.info("Redis pool closed")


app = FastAPI(title="Auth Server", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.SERVER_CORS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.SERVER_IP,
        port=settings.SERVER_PORT,
        reload=True,
    )