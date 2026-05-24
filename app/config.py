from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(Path(__file__).parent.parent, ".env"),
        env_file_encoding="utf-8",
    )

    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-change-in-prod"
    JWT_SECRET: str = "jwt-dev-secret"
    JWT_ACCESS_TTL: int = 900
    JWT_REFRESH_TTL: int = 2592000

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres123@localhost:5432/bio_erp"

    TEMPLATES_DIR: str = str(Path(__file__).parent / "templates")
    STATIC_DIR: str = str(Path(__file__).parent / "static")
    LOG_LEVEL: str = "INFO"

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_EMAIL: str = "admin@bioerp.local"
    ADMIN_FULL_NAME: str = "System Admin"


settings = Settings()
