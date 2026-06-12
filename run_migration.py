"""
run_migration.py — Apply document_system.sql migration
Auto-detects PostgreSQL vs SQLite, idempotent.
"""

import subprocess, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
MIGRATION_SQL = PROJECT_ROOT / "migrations" / "document_system.sql"
SQLITE_DB = PROJECT_ROOT / "bio_erp.db"


def log(msg, ok=True):
    icon = "[OK]" if ok else "[FAIL]"
    print(f"{icon} {msg}")


def main():
    print("=== Document System Migration ===\n")

    if not MIGRATION_SQL.exists():
        log(f"Migration file not found: {MIGRATION_SQL}", False)
        sys.exit(1)

    # Try PostgreSQL first
    try:
        import psycopg2

        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="bio_erp",
            user="postgres",
            password=os.environ.get(
                "PG_PASSWORD", ""
            ),  # moved to .env by audit fix 12.5,
        )
        cur = conn.cursor()
        sql = MIGRATION_SQL.read_text(encoding="utf-8")
        cur.execute(sql)
        conn.commit()

        # Verify tables
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('supporting_documents','document_modules')"
        )
        count = cur.fetchone()[0]
        log(f"PostgreSQL migration applied ({count}/2 tables verified)")
        cur.close()
        conn.close()
        return
    except ImportError:
        log("psycopg2 not available, trying SQLite...")
    except Exception as e:
        log(f"PostgreSQL connection failed: {e}", False)
        log("Trying SQLite...")

    # Fallback: SQLite
    if not SQLITE_DB.exists():
        log(f"SQLite DB not found: {SQLITE_DB}", False)
        log("No database connection available. Apply manually:", False)
        log(f"  psql -d bio_erp -f {MIGRATION_SQL}")
        log(f"  or: sqlite3 {SQLITE_DB} < {MIGRATION_SQL}")
        sys.exit(1)

    import sqlite3

    conn = sqlite3.connect(str(SQLITE_DB))
    cur = conn.cursor()

    # SQLite needs UUID workaround — use TEXT for id
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    sql = sql.replace(
        "UUID PRIMARY KEY DEFAULT gen_random_uuid()",
        "TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16))))",
    )
    sql = sql.replace("VARCHAR(", "TEXT(")
    sql = sql.replace("TIMESTAMP", "TEXT")
    sql = sql.replace("BIGINT", "INTEGER")

    for statement in sql.split(";"):
        stmt = statement.strip()
        if stmt:
            try:
                cur.execute(stmt)
            except Exception as e:
                if "already exists" not in str(e):
                    log(f"SQLite statement warning: {e}")

    conn.commit()

    # Verify
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('supporting_documents','document_modules')"
    )
    tables = [row[0] for row in cur.fetchall()]
    log(f"SQLite migration applied ({len(tables)}/2 tables: {', '.join(tables)})")
    conn.close()


if __name__ == "__main__":
    main()
