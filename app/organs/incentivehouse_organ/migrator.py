import pandas as pd
import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class ERPMigrator:
    def __init__(self, db_url: str):
        self.engine: Engine = create_engine(db_url)
        self.audit_log: List[Dict[str, Any]] = []
        self.batch_size = 500

    def ensure_staging_tables(self):
        dialect = self.engine.dialect.name
        if dialect == "sqlite":
            pk = "INTEGER PRIMARY KEY AUTOINCREMENT"
            varchar = "TEXT"
            numeric = "FLOAT"
            json_type = "TEXT"
            ts_type = "TEXT"
            default_ts = "CURRENT_TIMESTAMP"
            idx_exists = "SELECT name FROM sqlite_master WHERE type='index' AND name=:name"
        else:
            pk = "SERIAL PRIMARY KEY"
            varchar = "VARCHAR"
            numeric = "NUMERIC"
            json_type = "JSONB"
            ts_type = "TIMESTAMP"
            default_ts = "NOW()"
            idx_exists = "SELECT 1 FROM pg_indexes WHERE indexname=:name"

        def col(t: str) -> str:
            if t == "pk": return pk
            if t == "v50": return f"{varchar}(50)"
            if t == "v20": return f"{varchar}(20)"
            if t == "v30": return f"{varchar}(30)"
            if t == "v10": return f"{varchar}(10)"
            if t == "v3": return f"{varchar}(3)"
            if t == "num": return numeric
            if t == "json": return json_type
            if t == "ts": return ts_type
            return t

        tables_sql = {
            "bnk_staging": f"""
                CREATE TABLE IF NOT EXISTS bnk_staging (
                    id {col('pk')},
                    source_row_number INTEGER,
                    transaction_id {col('v50')},
                    transaction_date TEXT,
                    account_code {col('v20')},
                    description TEXT,
                    debit_amount {col('num')},
                    credit_amount {col('num')},
                    currency {col('v3')},
                    exchange_rate {col('num')},
                    amount_egp {col('num')},
                    sub_led_code INTEGER,
                    pnr_id INTEGER,
                    client_id INTEGER,
                    transaction_type {col('v30')},
                    cost_center {col('v50')},
                    reference_number {col('v50')},
                    validation_status {col('v20')},
                    validation_errors {col('json')},
                    migrated_at {col('ts')},
                    created_at {col('ts')} DEFAULT {default_ts}
                );
            """,
            "sal_staging": f"""
                CREATE TABLE IF NOT EXISTS sal_staging (
                    id {col('pk')},
                    source_row_number INTEGER,
                    transaction_id {col('v50')},
                    transaction_date TEXT,
                    account_code {col('v20')},
                    description TEXT,
                    debit_amount {col('num')},
                    credit_amount {col('num')},
                    currency {col('v3')},
                    exchange_rate {col('num')},
                    amount_egp {col('num')},
                    sub_led_code INTEGER,
                    pnr_id INTEGER,
                    client_id INTEGER,
                    tax_code {col('v10')},
                    tax_amount {col('num')},
                    net_amount {col('num')},
                    cost_center {col('v50')},
                    transaction_type {col('v20')},
                    validation_status {col('v20')},
                    validation_errors {col('json')},
                    migrated_at {col('ts')},
                    created_at {col('ts')} DEFAULT {default_ts}
                );
            """,
            "pur_staging": f"""
                CREATE TABLE IF NOT EXISTS pur_staging (
                    id {col('pk')},
                    source_row_number INTEGER,
                    transaction_id {col('v50')},
                    transaction_date TEXT,
                    due_date TEXT,
                    account_code {col('v20')},
                    description TEXT,
                    debit_amount {col('num')},
                    credit_amount {col('num')},
                    currency {col('v3')},
                    exchange_rate {col('num')},
                    amount_egp {col('num')},
                    sub_led_code INTEGER,
                    pnr_id INTEGER,
                    client_id INTEGER,
                    supplier_id INTEGER,
                    payment_terms {col('v20')},
                    cost_center {col('v50')},
                    transaction_type {col('v20')},
                    validation_status {col('v20')},
                    validation_errors {col('json')},
                    migrated_at {col('ts')},
                    created_at {col('ts')} DEFAULT {default_ts}
                );
            """,
            "evn_staging": f"""
                CREATE TABLE IF NOT EXISTS evn_staging (
                    id {col('pk')},
                    source_row_number INTEGER,
                    transaction_id {col('v50')},
                    transaction_date TEXT,
                    event_id {col('v50')},
                    account_code {col('v20')},
                    description TEXT,
                    debit_amount {col('num')},
                    credit_amount {col('num')},
                    currency {col('v3')},
                    exchange_rate {col('num')},
                    amount_egp {col('num')},
                    sub_led_code INTEGER,
                    pnr_id INTEGER,
                    client_id INTEGER,
                    cost_center {col('v50')},
                    transaction_type {col('v20')},
                    project_id {col('v50')},
                    reference_number {col('v50')},
                    validation_status {col('v20')},
                    validation_errors {col('json')},
                    migrated_at {col('ts')},
                    created_at {col('ts')} DEFAULT {default_ts}
                );
            """,
            "env_staging": f"""
                CREATE TABLE IF NOT EXISTS env_staging (
                    id {col('pk')},
                    source_row_number INTEGER,
                    transaction_id {col('v50')},
                    transaction_date TEXT,
                    account_code {col('v20')},
                    description TEXT,
                    debit_amount {col('num')},
                    credit_amount {col('num')},
                    currency {col('v3')},
                    exchange_rate {col('num')},
                    amount_egp {col('num')},
                    sub_led_code INTEGER,
                    pnr_id INTEGER,
                    client_id INTEGER,
                    cost_center {col('v50')},
                    transaction_type {col('v20')},
                    reference_number {col('v50')},
                    validation_status {col('v20')},
                    validation_errors {col('json')},
                    migrated_at {col('ts')},
                    created_at {col('ts')} DEFAULT {default_ts}
                );
            """,
        }
        with self.engine.connect() as conn:
            for table_name, ddl in tables_sql.items():
                conn.execute(text(ddl.strip()))
                index_defs = {
                    "bnk_staging": [("idx_bnk_tid", "transaction_id"), ("idx_bnk_date", "transaction_date")],
                    "sal_staging": [("idx_sal_tid", "transaction_id")],
                    "pur_staging": [("idx_pur_tid", "transaction_id")],
                    "evn_staging": [("idx_evn_tid", "transaction_id"), ("idx_evn_event", "event_id")],
                    "env_staging": [("idx_env_tid", "transaction_id")],
                }
                for idx_name, idx_col in index_defs.get(table_name, []):
                    result = conn.execute(text(idx_exists), {"name": idx_name})
                    if result.fetchone() is None:
                        conn.execute(text(f"CREATE INDEX {idx_name} ON {table_name}({idx_col})"))
            conn.commit()

    def stage_data(self, df: pd.DataFrame, module: str, errors: list) -> Dict[str, Any]:
        table_map = {
            "Bnk": "bnk_staging",
            "Sal": "sal_staging",
            "Pur": "pur_staging",
            "Evn": "evn_staging",
            "Env": "env_staging",
        }
        table_name = table_map.get(module)
        if not table_name:
            raise ValueError(f"Unknown module: {module}")

        df_out = df.copy()
        df_out.columns = [c.lower() for c in df_out.columns]
        error_rows = {e["row_index"] for e in errors if e["severity"] == "ERROR"}
        warning_rows = {e["row_index"] for e in errors}
        df_out["validation_status"] = df_out.index.to_series().apply(
            lambda i: "FAIL" if i in error_rows else ("WARNING" if i in warning_rows else "PASS")
        )
        df_out["validation_errors"] = df_out.index.to_series().apply(
            lambda i: json.dumps([e for e in errors if e["row_index"] == i])
        )
        df_out["migrated_at"] = datetime.now()
        df_out["source_row_number"] = df_out.index

        total_rows = len(df_out)
        col_map = {
            "transaction_id": "transaction_id",
            "transaction_date": "transaction_date",
            "description_norm": "description",
            "sub_led_code": "sub_led_code",
            "pnr_id": "pnr_id",
            "client_id": "client_id",
            "currency": "currency",
            "fx_rate": "exchange_rate",
            "amount_egp": "amount_egp",
            "validation_status": "validation_status",
            "validation_errors": "validation_errors",
            "migrated_at": "migrated_at",
            "source_row_number": "source_row_number",
        }
        if "account" in df_out.columns:
            col_map["account"] = "account_code"
        if "debit" in df_out.columns:
            col_map["debit"] = "debit_amount"
        if "credit" in df_out.columns:
            col_map["credit"] = "credit_amount"
        if "debit_amount" in df_out.columns:
            col_map["debit_amount"] = "debit_amount"
        if "credit_amount" in df_out.columns:
            col_map["credit_amount"] = "credit_amount"
        if "reference" in df_out.columns:
            col_map["reference"] = "reference_number"
        if "tax_amount" in df_out.columns:
            col_map["tax_amount"] = "tax_amount"
        if "net_amount" in df_out.columns:
            col_map["net_amount"] = "net_amount"
        if "tax_code" in df_out.columns:
            col_map["tax_code"] = "tax_code"
        if "due_date" in df_out.columns:
            col_map["due_date"] = "due_date"
        if "supplier_id" in df_out.columns:
            col_map["supplier_id"] = "supplier_id"
        if "payment_terms" in df_out.columns:
            col_map["payment_terms"] = "payment_terms"
        if "event_id" in df_out.columns:
            col_map["event_id"] = "event_id"
        if "project_id" in df_out.columns:
            col_map["project_id"] = "project_id"
        if "cost_center" in df_out.columns:
            col_map["cost_center"] = "cost_center"
        if "transaction_type" in df_out.columns:
            col_map["transaction_type"] = "transaction_type"
        if "original_amount" in df_out.columns:
            pass

        mapped_columns = [v for k, v in col_map.items() if k in df_out.columns]
        placeholders = ",".join([f":{c}" for c in mapped_columns])
        col_list = ",".join(mapped_columns)
        insert_sql = text(f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})")
        with self.engine.connect() as conn:
            for start in range(0, total_rows, self.batch_size):
                end = min(start + self.batch_size, total_rows)
                batch = df_out.iloc[start:end]
                params = []
                for _, row in batch.iterrows():
                    row_dict = {}
                    for df_col, sql_col in col_map.items():
                        if df_col not in df_out.columns:
                            continue
                        val = row[df_col]
                        if isinstance(val, datetime):
                            val = val.isoformat()
                        elif pd.isna(val):
                            val = None
                        elif isinstance(val, (np.integer,)):
                            val = int(val)
                        elif isinstance(val, (np.floating,)):
                            val = float(val)
                        row_dict[sql_col] = val
                    params.append(row_dict)
                conn.execute(insert_sql, params)
            conn.commit()

        result = {
            "module": module,
            "table": table_name,
            "total_rows": total_rows,
            "pass_count": int((df_out["validation_status"] == "PASS").sum()),
            "warning_count": int((df_out["validation_status"] == "WARNING").sum()),
            "fail_count": int((df_out["validation_status"] == "FAIL").sum()),
            "migrated_at": datetime.now().isoformat(),
        }
        self.audit_log.append(result)
        return result

    def check_existing_ids(self, df: pd.DataFrame, module: str) -> bool:
        table_map = {
            "Bnk": "bnk_staging", "Sal": "sal_staging", "Pur": "pur_staging",
            "Evn": "evn_staging", "Env": "env_staging",
        }
        table_name = table_map.get(module)
        if not table_name:
            return False
        if "TRANSACTION_ID" not in df.columns:
            return False
        ids = df["TRANSACTION_ID"].dropna().unique().tolist()
        if not ids:
            return False
        with self.engine.connect() as conn:
            placeholders = ",".join([f":id{i}" for i in range(len(ids))])
            params = {f"id{i}": v for i, v in enumerate(ids)}
            result = conn.execute(
                text(f"SELECT DISTINCT transaction_id FROM {table_name} WHERE transaction_id IN ({placeholders})"),
                params,
            )
            existing = {r[0] for r in result.fetchall()}
        return bool(existing)

    def count_existing(self, module: str) -> set:
        table_map = {
            "Bnk": "bnk_staging", "Sal": "sal_staging", "Pur": "pur_staging",
            "Evn": "evn_staging", "Env": "env_staging",
        }
        table_name = table_map.get(module)
        if not table_name:
            return set()
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT DISTINCT transaction_id FROM {table_name}"))
            return {r[0] for r in result.fetchall()}

    def generate_audit_report(self) -> Dict[str, Any]:
        return {
            "report_generated_at": datetime.now().isoformat(),
            "migrator_version": "1.0.0-access-free",
            "total_modules": len(self.audit_log),
            "modules": self.audit_log,
            "summary": {
                "total_records": sum(m["total_rows"] for m in self.audit_log),
                "total_pass": sum(m["pass_count"] for m in self.audit_log),
                "total_warning": sum(m["warning_count"] for m in self.audit_log),
                "total_fail": sum(m["fail_count"] for m in self.audit_log),
            },
        }

    def save_audit_report(self, output_dir: str = "audit_reports") -> Path:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        report = self.generate_audit_report()
        filename = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(output_dir) / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        return filepath
