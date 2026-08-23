"""
SQL Server 2022 Database Configuration for Bio-ERP
Replaces PostgreSQL connection with mssql+pyodbc
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

# Connection string — update with your credentials
# Format: mssql+pyodbc://username:password@server/database?driver=ODBC+Driver+17+for+SQL+Server
DATABASE_URL = os.getenv(
    "DATABASE_URL_MSSQL",
    "mssql+pyodbc://./EBUILD_ERP?"
    "driver=ODBC+Driver+17+for+SQL+Server"
    "&TrustServerCertificate=yes"
    "&Encrypt=yes"
    "&trusted_connection=yes"
)

# SQLAlchemy engine with SQL Server optimizations.
# pyodbc is Windows-only in practice (needs unixODBC headers on Linux);
# degrade gracefully so clean checkouts can still import the app tree.
try:
    import pyodbc  # noqa: F401
except ImportError:
    pyodbc = None

if pyodbc is not None:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
        connect_args={
            "timeout": 30,
            "TrustServerCertificate": "yes",
        }
    )

    @event.listens_for(engine, "connect")
    def set_sql_server_pragmas(dbapi_conn, connection_record):
        """Set SQL Server session settings on connect."""
        cursor = dbapi_conn.cursor()
        cursor.execute("SET ANSI_NULLS ON")
        cursor.execute("SET QUOTED_IDENTIFIER ON")
        cursor.execute("SET NOCOUNT OFF")
        cursor.close()

else:
    engine = None


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_mssql_database():
    """Initialize all tables in SQL Server."""
    print("SQL Server tables should already exist from T-SQL deployment.")
    print("Use Base.metadata.create_all(bind=engine) only for new tables.")
