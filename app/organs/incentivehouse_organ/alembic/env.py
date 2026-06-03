"""
Alembic env for the IncentiveHouse ERP organ.

When the Docker container starts, ``alembic upgrade head`` should create
all 27 organ tables (5 *_staging, 1 audit, plus 21 master / lifecycle /
reconciliation / config tables).  This env registers IncentiveBase's
metadata so autogenerate works against the same source of truth the
FastAPI app uses.

Configuration is read from env vars:
  DATABASE_URL          (async)  - ``postgresql+asyncpg://...`` or
                                     ``sqlite+aiosqlite:///./foo.db``
  SYNC_DATABASE_URL     (sync)   - used for offline SQL emit
  ALEMBIC_INI_PATH      (optional path to alembic.ini; default: ./alembic.ini)
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# ---------------------------------------------------------------------------
# Make ``app.organs.incentivehouse_organ`` importable when this file is
# invoked by ``alembic -x ...`` from the project root.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # alembic/ -> organ/ -> organs/ -> app/
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Import the SQLAlchemy ``Base`` that owns the 27 ORM models.
# ---------------------------------------------------------------------------
from app.organs.incentivehouse_organ.models import IncentiveBase  # noqa: E402
from app.organs.incentivehouse_organ import models_production  # noqa: E402, F401 — register production models on IncentiveBase

config = context.config

# Inject the runtime DB URL (env wins over alembic.ini)
_runtime_url = os.getenv("DATABASE_URL")
if _runtime_url:
    # Alembic wants a *sync* URL.  Strip the async driver prefix.
    _sync_url = _runtime_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    config.set_main_option("sqlalchemy.url", _sync_url)

if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        # Config file may not exist when running ad-hoc - that's fine.
        pass

target_metadata = IncentiveBase.metadata


# ---------------------------------------------------------------------------
# Offline (emit SQL script without a live connection)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url and "sqlite" in url,  # SQLite needs batch mode
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online (use a live DB connection)
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = config.get_main_option("sqlalchemy.url")
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        is_sqlite = "sqlite" in (url or "")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
