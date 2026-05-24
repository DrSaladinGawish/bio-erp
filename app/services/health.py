import asyncio
import os
import shutil
from datetime import datetime
from datetime import timezone
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.eta_client import ETAClient
from app.config import get_settings

settings = get_settings()


class HealthCheck:
    @staticmethod
    async def check_database() -> dict:
        try:
            async with AsyncSessionLocal() as db:
                start = datetime.utcnow()
                await db.execute(text("SELECT 1"))
                latency = (datetime.utcnow() - start).total_seconds()
                return {
                    "status": "healthy",
                    "latency_ms": round(latency * 1000, 2),
                    "type": "postgresql"
                    if "postgres" in str(settings.DATABASE_URL)
                    else "sqlite",
                }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    async def check_eta_api() -> dict:
        if not getattr(settings, "eta_client_id", None):
            return {
                "status": "degraded",
                "error": "ETA not configured (no client_id)",
                "authenticated": False,
            }
        try:
            start = datetime.utcnow()
            token = await ETAClient._get_token()
            latency = (datetime.utcnow() - start).total_seconds()
            return {
                "status": "healthy" if token else "degraded",
                "latency_ms": round(latency * 1000, 2),
                "authenticated": bool(token),
                "environment": "production"
                if "api.eta.gov.eg" in str(getattr(settings, "eta_base_url", ""))
                else "preprod",
            }
        except Exception as e:
            return {"status": "degraded", "error": str(e), "authenticated": False}

    @staticmethod
    async def check_disk_space() -> dict:
        try:
            path = "/app" if os.path.exists("/app") else os.getcwd()
            total, used, free = shutil.disk_usage(path)
            percent = (used / total) * 100
            return {
                "status": "healthy" if percent < 90 else "critical",
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "percent_used": round(percent, 1),
            }
        except Exception as e:
            return {"status": "unknown", "error": str(e)}

    @staticmethod
    async def check_redis() -> dict:
        try:
            import redis as sync_redis

            r = sync_redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True,
                socket_connect_timeout=3,
            )
            info = r.info()
            r.close()
            return {
                "status": "healthy",
                "version": info.get("redis_version", "unknown"),
                "used_memory_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            return {"status": "degraded", "error": str(e)}

    @staticmethod
    async def check_celery() -> dict:
        try:
            from app.celery_app import celery_app

            insp = celery_app.control.inspect(timeout=2)
            stats = insp.stats()
            if stats:
                workers = list(stats.keys())
                return {"status": "healthy", "workers": workers}
            return {"status": "degraded", "error": "No Celery workers responding"}
        except Exception as e:
            return {"status": "degraded", "error": str(e)}

    @staticmethod
    async def check_ollama() -> dict:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as c:
                resp = await c.get("http://localhost:11434/api/tags")
                if resp.status_code == 200:
                    models = [m["name"] for m in resp.json().get("models", [])]
                    return {"status": "healthy", "models": models}
                return {"status": "degraded", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "degraded", "error": str(e)}

    @staticmethod
    async def full_check() -> dict:
        db, eta, disk, redis, celery, ollama = await asyncio.gather(
            HealthCheck.check_database(),
            HealthCheck.check_eta_api(),
            HealthCheck.check_disk_space(),
            HealthCheck.check_redis(),
            HealthCheck.check_celery(),
            HealthCheck.check_ollama(),
        )

        statuses = [db, eta, disk, redis, celery, ollama]
        overall = "healthy"
        for s in statuses:
            if s.get("status") == "unhealthy":
                overall = "unhealthy"
                break
            if s.get("status") == "critical":
                overall = "critical"
            if s.get("status") == "degraded" and overall == "healthy":
                overall = "degraded"

        return {
            "status": overall,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": db,
                "eta_api": eta,
                "disk": disk,
                "redis": redis,
                "celery": celery,
                "ollama": ollama,
            },
        }
