import os
import time
from functools import wraps
from fastapi import HTTPException, Request


def _get_redis():
    try:
        import redis as sync_redis

        return sync_redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
    except Exception:
        return None


def rate_limit(max_per_minute: int, path_prefix: str = ""):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            if request is None:
                return await func(*args, **kwargs)

            r = _get_redis()
            if r is None:
                return await func(*args, **kwargs)

            key = f"ratelimit:{path_prefix}:{request.client.host if request.client else 'unknown'}"
            window = 60
            now = time.time()
            r.pipeline().zremrangebyscore(key, 0, now - window).execute()
            count = r.zcard(key)
            if count and int(count) >= max_per_minute:
                raise HTTPException(
                    status_code=429, detail="Rate limit exceeded. Try again later."
                )

            r.pipeline().zadd(key, {str(now): now}).expire(key, window).execute()
            return await func(*args, **kwargs)

        return wrapper

    return decorator
