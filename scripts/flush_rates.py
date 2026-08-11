import asyncio
from app.core.redis import get_redis

async def flush():
    r = await get_redis()
    if r:
        keys = await r.keys("rate_limit:*")
        if keys:
            await r.delete(*keys)
            print(f"Flushed {len(keys)} rate limit keys")
        else:
            print("No rate limit keys")

asyncio.run(flush())
