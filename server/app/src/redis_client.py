import redis.asyncio as redis
from src.config import settings


redis_pool = redis.BlockingConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    timeout=5,
    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    retry_on_timeout=True,
    health_check_interval=30,
)


def get_redis_client() -> redis.Redis:
    """Возвращает клиент Redis, подключённый к общему пулу."""
    return redis.Redis(connection_pool=redis_pool)