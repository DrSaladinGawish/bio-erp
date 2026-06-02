import os
import json
from typing import Optional, Any
from datetime import timedelta

import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = await aioredis.from_url(
            REDIS_URL, decode_responses=True
        )
    return _client


async def close_redis():
    global _client
    if _client:
        await _client.close()
        _client = None


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    val = await r.get(key)
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val


async def cache_set(
    key: str, value: Any, ttl: int = 300
) -> None:
    r = await get_redis()
    serialized = json.dumps(value, default=str)
    await r.setex(key, timedelta(seconds=ttl), serialized)


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def cache_invalidate_pattern(pattern: str) -> None:
    r = await get_redis()
    cursor = 0
    while True:
        cursor, keys = await r.scan(
            cursor, match=pattern, count=100
        )
        if keys:
            await r.delete(*keys)
        if cursor == 0:
            break
