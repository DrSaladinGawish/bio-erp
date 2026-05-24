import json
import os
from typing import Any

_ALERT_CHANNEL = "variance_alerts"
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis

            _redis_client = aioredis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True,
            )
        except Exception:
            _redis_client = None
    return _redis_client


def publish_variance_alert(alert: dict[str, Any]) -> None:
    try:
        import redis as sync_redis

        r = sync_redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
        r.publish(_ALERT_CHANNEL, json.dumps(alert))
        r.close()
    except Exception:
        pass


async def subscribe_alerts():
    r = _get_redis()
    if r is None:
        return
    pubsub = r.pubsub()
    await pubsub.subscribe(_ALERT_CHANNEL)
    async for message in pubsub.listen():
        if message["type"] == "message":
            yield json.loads(message["data"])
