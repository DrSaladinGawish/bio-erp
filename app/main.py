from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import get_async_engine, get_db, init_db
from app.routers import accounting

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BIO_ERP v5...")
    engine = get_async_engine()
    try:
        async with engine.begin() as conn:
            from app.models import Base
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.warning("Could not create tables (may already exist): %s", e)

    from app.auth import hash_password
    from app.models import User
    async for db in get_db():
        try:
            result = await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
            existing = result.scalar_one_or_none()
            if not existing:
                admin = User(
                    username=settings.ADMIN_USERNAME,
                    email=settings.ADMIN_EMAIL,
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    full_name_en=settings.ADMIN_FULL_NAME,
                    is_superuser=True,
                )
                db.add(admin)
                await db.commit()
                logger.info("Admin user created: %s", settings.ADMIN_USERNAME)
        finally:
            await db.close()
        break
    yield
    logger.info("Shutting down BIO_ERP v5...")


app = FastAPI(
    title="BIO_ERP v5",
    version="5.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(accounting.router, prefix="/api/v1/accounting")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    if "HX-Request" in request.headers:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            "<div class='alert alert-danger'>An unexpected error occurred.</div>",
            status_code=500,
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root():
    return {"message": "BIO_ERP v5", "version": "5.0.0"}
