"""add readonly db role for AI SQL engine

Revision ID: a1b2c3d4e5f6
Revises: 538754350731
Create Date: 2026-08-20 12:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import os

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "538754350731"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE_NAME = "bio_erp_reader"
ROLE_PASSWORD = os.environ.get("BIO_ERP_READER_PASSWORD", "DXqF5mW7Hcz4AIg9nSCMFroeyqZegS74thwxuxQVwPQ")
DB_NAME = os.environ.get("POSTGRES_DB", "bio_erp")


def upgrade() -> None:
    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{ROLE_NAME}') THEN
                CREATE ROLE {ROLE_NAME} LOGIN PASSWORD '{ROLE_PASSWORD}';
            END IF;
        END
        $$;
    """)
    op.execute(f"GRANT CONNECT ON DATABASE {DB_NAME} TO {ROLE_NAME};")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {ROLE_NAME};")
    op.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {ROLE_NAME};")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {ROLE_NAME};")


def downgrade() -> None:
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM {ROLE_NAME};")
    op.execute(f"REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM {ROLE_NAME};")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {ROLE_NAME};")
    op.execute(f"REVOKE CONNECT ON DATABASE {DB_NAME} FROM {ROLE_NAME};")
    op.execute(f"DROP ROLE IF EXISTS {ROLE_NAME};")
