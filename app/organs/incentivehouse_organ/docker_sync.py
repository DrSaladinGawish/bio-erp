"""
P2-C1: Docker SQL Server → PostgreSQL Sync
Runs when Docker engine is back online. Detects changes, replays in PostgreSQL.
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

SQL_SERVER = {
    "host": os.getenv("SQL_HOST", "localhost"),
    "port": int(os.getenv("SQL_PORT", "1433")),
    "database": os.getenv("SQL_DB", "IHE_ERP"),
    "user": os.getenv("SQL_USER", "sa"),
    "password": os.getenv("SQL_PASSWORD", "IHE_ERP_2024!"),
}

POSTGRES = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "database": os.getenv("PG_DB", "bio_erp"),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD", "postgres123"),
}

SYNC_STATE_FILE = Path("D:/ERP System/BIO_ERP/sync_state.json")

TABLE_MAP = {
    "Clients": {
        "pg_table": "clients",
        "pk": "ClientCode",
        "pg_pk": "client_code",
        "columns": {
            "ClientCode": "client_code",
            "ClientName": "name_en",
            "TaxID": "tax_id",
            "Email": "email",
            "Phone": "phone",
            "CreditLimit": "credit_limit",
            "Status": "status",
        },
    },
    "PNRMaster": {
        "pg_table": "events",
        "pk": "PNRNo",
        "pg_pk": "pnr_id",
        "columns": {
            "PNRNo": "pnr_id",
            "ClientCode": "client_id",
            "EventDate": "event_date",
            "EventDescription": "event_name",
            "Pax": "expected_pax",
            "TotalAmount": "gross_sales",
            "Currency": "currency",
            "Status": "lifecycle_status",
        },
    },
    "BankTransactions": {
        "pg_table": "bank_trnx_staging",
        "pk": "TrnxNum",
        "pg_pk": "transaction_number",
        "columns": {
            "TrnxNum": "transaction_number",
            "TrnxDate": "tx_date",
            "BankCode": "bank_account",
            "Narration": "description",
            "Debit": "debit_amount",
            "Credit": "credit_amount",
            "SubLedCode": "sub_ledger_code",
        },
    },
    "Staff": {
        "pg_table": "staff",
        "pk": "StaffID",
        "pg_pk": "id",
        "columns": {
            "StaffID": "id",
            "StaffName": "name",
            "Email": "email",
            "Role": "role",
            "Department": "department",
            "Status": "status",
        },
    },
    "Vendors": {
        "pg_table": "suppliers",
        "pk": "VendorID",
        "pg_pk": "id",
        "columns": {
            "VendorID": "id",
            "VendorName": "name",
            "Category": "category",
            "Email": "email",
            "Phone": "phone",
            "Rating": "rating",
            "Status": "status",
        },
    },
}


class SyncState:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.state = self._load()

    def _load(self) -> Dict:
        if self.filepath.exists():
            with open(self.filepath) as f:
                return json.load(f)
        return {}

    def save(self):
        with open(self.filepath, "w") as f:
            json.dump(self.state, f, indent=2, default=str)

    def get_last_sync(self, table: str) -> Optional[datetime]:
        ts = self.state.get(table, {}).get("last_sync")
        return datetime.fromisoformat(ts) if ts else None

    def set_last_sync(self, table: str, ts: datetime):
        self.state.setdefault(table, {})["last_sync"] = ts.isoformat()


class DockerSyncEngine:
    def __init__(self):
        self.state = SyncState(SYNC_STATE_FILE)
        self.sql_conn = None
        self.pg_conn = None

    def sync_all(self) -> Dict:
        print(f"Docker Sync Engine — {datetime.now().isoformat()}")
        try:
            import pyodbc
            import psycopg2

            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={SQL_SERVER['host']},{SQL_SERVER['port']};"
                f"DATABASE={SQL_SERVER['database']};"
                f"UID={SQL_SERVER['user']};PWD={SQL_SERVER['password']};"
                f"TrustServerCertificate=yes;"
            )
            self.sql_conn = pyodbc.connect(conn_str, timeout=10)
            self.pg_conn = psycopg2.connect(**POSTGRES)

            results = {}
            for table, mapping in TABLE_MAP.items():
                results[table] = self._sync_table(table, mapping)
            self.state.save()
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "results": results,
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
        finally:
            if self.sql_conn:
                self.sql_conn.close()
            if self.pg_conn:
                self.pg_conn.close()

    def _sync_table(self, table: str, mapping: Dict) -> Dict:
        since = self.state.get_last_sync(table)
        cursor = self.sql_conn.cursor()
        cursor.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? AND COLUMN_NAME = 'ModifiedDate'",
            (table,),
        )
        has_modified = cursor.fetchone() is not None
        sql_cols = ", ".join(mapping["columns"].keys())
        if has_modified and since:
            cursor.execute(
                f"SELECT {sql_cols} FROM {table} WHERE ModifiedDate >= ? ORDER BY {mapping['pk']}",
                (since,),
            )
        else:
            cursor.execute(f"SELECT {sql_cols} FROM {table} ORDER BY {mapping['pk']}")
        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        if not rows:
            return {"synced": 0}

        pg_cols = list(mapping["columns"].values())
        pg_table = mapping["pg_table"]
        pk = mapping["pg_pk"]
        placeholders = ", ".join(["%s"] * len(pg_cols))
        update_set = ", ".join([f"{c} = EXCLUDED.{c}" for c in pg_cols if c != pk])
        upsert_sql = f"INSERT INTO {pg_table} ({', '.join(pg_cols)}) VALUES ({placeholders}) ON CONFLICT ({pk}) DO UPDATE SET {update_set}"

        pg_cursor = self.pg_conn.cursor()
        synced = 0
        for row in rows:
            values = [row.get(sql_col) for sql_col in mapping["columns"].keys()]
            try:
                pg_cursor.execute(upsert_sql, values)
                synced += 1
            except Exception as e:
                print(f"ERROR on {row.get(mapping['pk'])}: {e}")
        self.pg_conn.commit()
        self.state.set_last_sync(table, datetime.now())
        return {"synced": synced}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Docker SQL Server to PostgreSQL Sync")
    parser.add_argument("--sync", action="store_true", help="Run sync")
    args = parser.parse_args()
    if args.sync:
        engine = DockerSyncEngine()
        engine.sync_all()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
