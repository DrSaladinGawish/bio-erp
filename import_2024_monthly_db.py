"""
import_2024_monthly_db.py — Import 2024 monthly batch JSONL into supporting_documents
"""

import json, sys, uuid
from datetime import datetime
from pathlib import Path

BATCH_LOG = Path(r"D:\Data_Sources\docs\2024-Monthly\ingest_batch.jsonl")
DRY_RUN = "--dry-run" in sys.argv

try:
    import psycopg2

    DB = "postgresql"
    PG_CONFIG = {
        "host": "localhost",
        "port": 5432,
        "dbname": "bio_erp",
        "user": "postgres",
        "password": "postgres123",
    }
except ImportError:
    try:
        import sqlite3

        DB = "sqlite"
        DB_PATH = Path(r"D:\ERP System\BIO_ERP\bio_erp.db")
    except ImportError:
        print("ERROR: No database driver available")
        sys.exit(1)


def connect():
    if DB == "postgresql":
        conn = psycopg2.connect(**PG_CONFIG)
        conn.autocommit = True
        return conn, conn.cursor()
    else:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn, conn.cursor()


def main():
    print("=== 2024 Monthly DB Import ===")
    if DRY_RUN:
        print("[DRY RUN — no DB changes]")

    if not BATCH_LOG.exists():
        print(f"ERROR: Batch log not found: {BATCH_LOG}")
        print("Run ingest_2024_monthly.py first")
        sys.exit(1)

    records = []
    with open(BATCH_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"Loaded {len(records)} records from batch log")

    if not records:
        print("Nothing to import")
        return

    conn, cur = connect()
    now = datetime.utcnow().isoformat()
    inserted = 0
    skipped = 0
    errors = 0

    for rec in records:
        try:
            doc_id = str(uuid.uuid4())
            hash_val = rec["file_hash_sha256"]

            if DB == "postgresql":
                cur.execute(
                    "SELECT COUNT(*) FROM supporting_documents WHERE file_hash_sha256 = %s",
                    (hash_val,),
                )
                exists = cur.fetchone()[0] > 0
            else:
                cur.execute(
                    "SELECT COUNT(*) FROM supporting_documents WHERE file_hash_sha256 = ?",
                    (hash_val,),
                )
                row = cur.fetchone()
                exists = row[0] > 0 if isinstance(row, tuple) else row["COUNT(*)"] > 0

            if exists:
                skipped += 1
                continue

            if not DRY_RUN:
                if DB == "postgresql":
                    cur.execute(
                        """
                        INSERT INTO supporting_documents
                        (id, module_name, function_name, transaction_table, transaction_id,
                         original_usb_path, archive_path, file_hash_sha256, file_size_bytes,
                         file_name, file_ext, status, uploaded_by, ingested_at, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                        (
                            doc_id,
                            rec["module_name"],
                            rec["function_name"],
                            rec["transaction_table"],
                            rec["transaction_id"],
                            rec["original_usb_path"],
                            rec["archive_path"],
                            hash_val,
                            rec["file_size_bytes"],
                            rec["file_name"],
                            rec["file_ext"],
                            rec["status"],
                            rec["uploaded_by"],
                            now,
                            now,
                            now,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO supporting_documents
                        (id, module_name, function_name, transaction_table, transaction_id,
                         original_usb_path, archive_path, file_hash_sha256, file_size_bytes,
                         file_name, file_ext, status, uploaded_by, ingested_at, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            doc_id,
                            rec["module_name"],
                            rec["function_name"],
                            rec["transaction_table"],
                            rec["transaction_id"],
                            rec["original_usb_path"],
                            rec["archive_path"],
                            hash_val,
                            rec["file_size_bytes"],
                            rec["file_name"],
                            rec["file_ext"],
                            rec["status"],
                            rec["uploaded_by"],
                            now,
                            now,
                            now,
                        ),
                    )
                inserted += 1
            else:
                inserted += 1

        except Exception as e:
            print(f"  ERROR inserting {rec.get('file_name', '?')}: {e}")
            errors += 1

    linked = sum(1 for r in records if r.get("status") == "linked")

    print(f"\nInserted: {inserted}")
    print(f"Skipped (duplicate hash): {skipped}")
    print(f"Errors: {errors}")
    print(f"Linked: {linked}")

    if not DRY_RUN:
        cur.execute("SELECT COUNT(*) FROM supporting_documents")
        total = cur.fetchone()[0]
        print(f"Total records in supporting_documents: {total}")
        print("Filter by archive_path LIKE '%2024-Monthly%'")

    conn.close()


if __name__ == "__main__":
    main()
