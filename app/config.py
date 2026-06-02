from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(Path(__file__).parent.parent, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-change-in-prod"
    JWT_SECRET: str = "jwt-dev-secret"
    JWT_ACCESS_TTL: int = 900
    JWT_REFRESH_TTL: int = 2592000

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres123@localhost:5432/bio_erp"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres123@localhost:5432/bio_erp"

    TEMPLATES_DIR: str = str(Path(__file__).parent / "templates")
    STATIC_DIR: str = str(Path(__file__).parent / "static")
    LOG_LEVEL: str = "INFO"

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_EMAIL: str = "admin@bioerp.local"
    ADMIN_FULL_NAME: str = "System Admin"

    # CBE currency sync
    CBE_API_URL: str = "https://www.cbe.org.eg/api/currency-rates"
    CBE_API_KEY: str = ""

    # SMTP / Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASS: str | None = None
    FROM_EMAIL: str | None = None

    # ETA e-invoicing
    ETA_BASE_URL: str = "https://api.preprod.eta.gov.eg"
    ETA_CLIENT_ID: str | None = None
    ETA_CLIENT_SECRET: str | None = None
    COMPANY_TAX_ID: str = "123456789"
    COMPANY_NAME: str = "BIO-ERP Company"
    COMPANY_ACTIVITY_CODE: str = "6201"
    ETA_PRIVATE_KEY_PATH: str = "./keys/eta_private.pem"
    ETA_PUBLIC_KEY_PATH: str = "./keys/eta_public.pem"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Defaults
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # EventCore integration
    eventcore_base_url: str = "http://localhost:8001"
    BIO_ERP_BRIDGE_TOKEN: str = "ec-bridge-token-dev"

    DEFAULT_BRANCH_ID: int = 1
    DEFAULT_CURRENCY_ID: int = 1
    VAT_RATE_EG: float = 0.14
    VAT_RATE_UAE: float = 0.05


settings = Settings()


def get_settings() -> Settings:
    return settings
