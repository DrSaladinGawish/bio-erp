"""Runtime health check used by CI and ops.

Verifies, in order:
1. Application settings load (env validation).
2. FastAPI app imports cleanly.
3. Database connectivity via SELECT 1.

Exit codes: 0 healthy, 1 unhealthy.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    try:
        from app.config import settings
    except Exception as exc:
        print(f"[FAIL] settings load: {exc}")
        return 1
    print("[ OK ] settings loaded")

    try:
        from app.main import app
    except Exception as exc:
        print(f"[FAIL] app import: {exc}")
        return 1
    print("[ OK ] FastAPI app imported")

    url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        async def _ping():
            engine = create_async_engine(url, pool_pre_ping=True)
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            finally:
                await engine.dispose()

        asyncio.run(_ping())
    except Exception as exc:
        print(f"[FAIL] database ping: {exc}")
        return 1
    print("[ OK ] database reachable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
