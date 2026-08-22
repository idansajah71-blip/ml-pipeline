import redis.asyncio as redis
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

settings = get_settings()

redis_client = None


async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        try:
            client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            await client.ping()
            redis_client = client
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Running without cache.")
            try:
                await client.aclose()
            except Exception:
                pass
            redis_client = None
    return redis_client


async def cache_get(key: str) -> str | None:
    client = await get_redis()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception as e:
        logger.warning(f"Redis cache_get error: {e}")
        return None


async def cache_set(key: str, value: str, expire: int = 3600) -> None:
    client = await get_redis()
    if client is None:
        return
    try:
        await client.set(key, value, ex=expire)
    except Exception as e:
        logger.warning(f"Redis cache_set error: {e}")


async def cache_delete(key: str) -> None:
    client = await get_redis()
    if client is None:
        return
    try:
        await client.delete(key)
    except Exception as e:
        logger.warning(f"Redis cache_delete error: {e}")
