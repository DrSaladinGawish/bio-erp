"""
Schema Alignment Verifier & Fixer
Compares actual PostgreSQL columns against what Phases 3-5 expect.
Run before deploying Phases 3-5 to catch mismatches.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Tuple

# ── CONFIG ──
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "bio_erp")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres123")

# ── EXPECTED SCHEMA (what Phases 3-5 need) ──
EXPECTED_SCHEMA = {
    "events": {
        "required": [
            "id",
            "client_id",
            "name_en",
            "event_type",
            "event_date",
            "lifecycle_status",
            "ops_team_id",
            "execution_date",
            "actual_pax",
            "actual_cost",
            "budget",
            "gross_sales",
            "currency",
            "expected_pax",
            "venue_id",
            "city",
            "country",
        ],
        "optional": ["name_ar", "description", "created_at", "updated_at"],
        "types": {
            "lifecycle_status": ["character varying", "varchar", "text"],
            "ops_team_id": ["integer", "bigint"],
            "execution_date": ["timestamp without time zone", "timestamp", "date"],
            "actual_pax": ["integer", "bigint", "numeric"],
            "actual_cost": ["numeric", "double precision", "real"],
            "budget": ["numeric", "double precision", "real"],
            "gross_sales": ["numeric", "double precision", "real"],
            "currency": ["character varying", "varchar", "text"],
        },
    },
    "clients": {
        "required": [
            "id",
            "name_en",
            "name_ar",
            "tax_id",
            "email",
            "phone",
            "credit_limit",
            "status",
        ],
        "optional": ["address", "city", "country", "created_at"],
    },
    "sales_line_items": {
        "required": ["id", "event_id", "category_name", "quantity", "unit_price"],
        "optional": [
            "sub_category",
            "uom",
            "buffer_percent",
            "vendor_id",
            "status",
            "notes",
        ],
        "types": {
            "uom": ["character varying", "varchar", "text"],
            "buffer_percent": ["numeric", "double precision", "real", "integer"],
            "vendor_id": ["integer", "bigint"],
            "status": ["character varying", "varchar", "text"],
        },
    },
    "staff": {
        "required": ["id", "name", "email", "role"],
        "optional": ["department", "phone", "status"],
    },
    "vendors": {  # or suppliers
        "required": ["id", "name", "category"],
        "optional": ["email", "phone", "rating", "currency", "status"],
    },
    "event_checkpoints": {
        "required": [
            "id",
            "event_id",
            "checkpoint_id",
            "label",
            "stage",
            "required",
            "completed_at",
            "completed_by",
            "notes",
        ],
        "optional": [
            "due_date",
            "sort_order",
            "linked_document_id",
            "linked_po_id",
            "linked_invoice_id",
            "extra_data",
        ],
    },
    "bank_trnx_staging": {
        "required": [
            "id",
            "transaction_number",
            "tx_date",
            "description",
            "debit_amount",
            "credit_amount",
        ],
        "optional": ["bank_account", "sub_ledger_code", "status"],
    },
}

# ── SQL FIXES ──
FIX_SQL = {
    "events": """
        -- Add missing lifecycle columns to events
        ALTER TABLE events 
            ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(20) DEFAULT 'draft',
            ADD COLUMN IF NOT EXISTS ops_team_id INTEGER,
            ADD COLUMN IF NOT EXISTS execution_date TIMESTAMP,
            ADD COLUMN IF NOT EXISTS actual_pax INTEGER,
            ADD COLUMN IF NOT EXISTS actual_cost NUMERIC(15,2),
            ADD COLUMN IF NOT EXISTS event_name VARCHAR(200),
            ADD COLUMN IF NOT EXISTS city VARCHAR(100),
            ADD COLUMN IF NOT EXISTS country VARCHAR(100),
            ADD COLUMN IF NOT EXISTS budget NUMERIC(15,2),
            ADD COLUMN IF NOT EXISTS gross_sales NUMERIC(15,2),
            ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'EGP';

        CREATE INDEX IF NOT EXISTS idx_events_lifecycle ON events(lifecycle_status);
        CREATE INDEX IF NOT EXISTS idx_events_ops_team ON events(ops_team_id);
        CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
    """,
    "sales_line_items": """
        ALTER TABLE sales_line_items
            ADD COLUMN IF NOT EXISTS uom VARCHAR(20),
            ADD COLUMN IF NOT EXISTS buffer_percent NUMERIC(5,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS vendor_id INTEGER,
            ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending',
            ADD COLUMN IF NOT EXISTS notes TEXT;
    """,
    "event_checkpoints": """
        CREATE TABLE IF NOT EXISTS event_checkpoints (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            checkpoint_id VARCHAR(50) NOT NULL,
            label VARCHAR(200) NOT NULL,
            stage VARCHAR(20) NOT NULL DEFAULT 'ops_assigned',
            required BOOLEAN DEFAULT TRUE,
            completed_at TIMESTAMP,
            completed_by VARCHAR(100),
            notes TEXT,
            due_date TIMESTAMP,
            sort_order INTEGER DEFAULT 0,
            linked_document_id INTEGER,
            linked_po_id INTEGER,
            linked_invoice_id INTEGER,
            extra_data JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_checkpoints_event ON event_checkpoints(event_id);
        CREATE INDEX IF NOT EXISTS idx_checkpoints_stage ON event_checkpoints(event_id, stage);
    """,
    "clients": """
        ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS name_ar VARCHAR(200),
            ADD COLUMN IF NOT EXISTS tax_id VARCHAR(50),
            ADD COLUMN IF NOT EXISTS credit_limit NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
    """,
}


def get_connection():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASSWORD
    )


def get_actual_columns(conn, table: str) -> List[Dict]:
    """Query information_schema for actual column definitions."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """,
            (table,),
        )
        return cur.fetchall()


def verify_table(conn, table: str, expected: Dict) -> Tuple[bool, List[str], List[str]]:
    """
    Returns: (is_valid, missing_columns, type_mismatches)
    """
    actual = get_actual_columns(conn, table)
    actual_names = {c["column_name"] for c in actual}
    actual_types = {c["column_name"]: c["data_type"] for c in actual}

    missing = []
    type_errors = []

    # Check required columns
    for col in expected.get("required", []):
        if col not in actual_names:
            missing.append(col)

    # Check type matches where specified
    for col, allowed_types in expected.get("types", {}).items():
        if col in actual_types:
            actual_type = actual_types[col].lower()
            if not any(t.lower() in actual_type for t in allowed_types):
                type_errors.append(
                    f"{col}: got {actual_type}, expected one of {allowed_types}"
                )

    is_valid = len(missing) == 0 and len(type_errors) == 0
    return is_valid, missing, type_errors


def apply_fixes(conn, table: str):
    """Apply SQL fixes for a given table."""
    if table in FIX_SQL:
        with conn.cursor() as cur:
            print(f"  Applying fixes for {table}...")
            cur.execute(FIX_SQL[table])
            conn.commit()
            print(f"  ✅ {table} fixed")


def main():
    print("=" * 60)
    print("BIO-ERP Schema Alignment Verifier — Phases 3-5")
    print("=" * 60)
    print(f"Connecting to PostgreSQL: {PG_HOST}:{PG_PORT}/{PG_DB}")

    try:
        conn = get_connection()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    print("✅ Connected")

    all_valid = True
    fix_needed = []

    for table, expected in EXPECTED_SCHEMA.items():
        print(f"Checking table: {table}")

        # Check if table exists
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = %s
                )
            """,
                (table,),
            )
            exists = cur.fetchone()[0]

        if not exists:
            print(f"  ⚠️  Table '{table}' does not exist — will be created by fixes")
            fix_needed.append(table)
            all_valid = False
            continue

        is_valid, missing, type_errors = verify_table(conn, table, expected)

        if missing:
            print(f"  ❌ Missing columns: {', '.join(missing)}")
            fix_needed.append(table)
        if type_errors:
            print(f"  ⚠️  Type mismatches: {', '.join(type_errors)}")
        if is_valid:
            print("  ✅ All required columns present and types match")
        else:
            all_valid = False
        print()

    # Summary
    print("=" * 60)
    if all_valid:
        print("✅ SCHEMA IS READY — Phases 3-5 can deploy without fixes")
    else:
        print(f"⚠️  {len(fix_needed)} table(s) need fixes: {', '.join(fix_needed)}")

        # Auto-fix prompt
        if len(sys.argv) > 1 and sys.argv[1] == "--fix":
            print("🔧 Applying fixes...")
            for table in fix_needed:
                apply_fixes(conn, table)
            print("All fixes applied. Re-run without --fix to verify.")
        else:
            print("To auto-fix, run: python schema_aligner.py --fix")
            print("Or manually apply the SQL in FIX_SQL dict above.")

    conn.close()
    print("=" * 60)


if __name__ == "__main__":
    main()
