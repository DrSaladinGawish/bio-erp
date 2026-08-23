import inspect
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
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is not None:
                try:
                    r = _get_redis()
                    if r is not None:
                        key = f"ratelimit:{path_prefix}:{request.client.host if request.client else 'unknown'}"
                        window = 60
                        now = time.time()
                        r.pipeline().zremrangebyscore(key, 0, now - window).execute()
                        count = r.zcard(key)
                        if count and int(count) >= max_per_minute:
                            raise HTTPException(
                                status_code=429,
                                detail="Rate limit exceeded. Try again later.",
                            )
                        r.pipeline().zadd(key, {str(now): now}).expire(
                            key, window
                        ).execute()
                except HTTPException:
                    raise
                except Exception:
                    # Limiter infrastructure failure must never take the
                    # endpoint down (fail-open).
                    pass

            return await func(*args, **kwargs)

        # FastAPI must dependency-inject against the ORIGINAL signature;
        # relying on __wrapped__ unwrapping is fragile across versions.
        wrapper.__signature__ = inspect.signature(func)
        return wrapper

    return decorator
