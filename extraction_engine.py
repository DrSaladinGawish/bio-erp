# ============================================================
# EXTRACTION ENGINE v2.2.3 — IncentiveHouse ERP
# ============================================================

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("extraction_engine")

# --- Database helper ---
DB_PATH = os.path.join(os.path.dirname(__file__), "incentivehouse.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_table_counts() -> Dict[str, int]:
    with get_db() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0]: 0 for row in cursor.fetchall()}
        for table in tables:
            try:
                c = conn.execute(f"SELECT COUNT(*) FROM {table}")
                tables[table] = c.fetchone()[0]
            except Exception:
                tables[table] = -1
        return tables

def resolve_source_file(filename: str) -> str:
    if os.path.isabs(filename):
        return filename
    candidates = [
        filename,
        os.path.join("data", filename),
        os.path.join("uploads", filename),
        os.path.join("Data Base", filename),          # ← ADDED
        os.path.join(os.path.dirname(__file__), filename),
        os.path.join(os.path.dirname(__file__), "data", filename),
        os.path.join(os.path.dirname(__file__), "Data Base", filename),  # ← ADDED
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.abspath(filename)

# ============================================================
# MASTER DATA — Maps actual Excel sheet names to DB tables
# ============================================================

def _resolve_master_table(sheet_name: str) -> Optional[str]:
    """Map Excel sheet names from Data_Base_Mtbls.xlsx to SQLite tables."""
    mapping = {
        # Categories
        "COA_Cat": "coa_categories_master",
        "Itm_Cat": "item_categories_master",
        # Master tables
        "COA_Mtble": "coa_master",
        "EINV_Itm_Mtble": "items_master",
        "Bud_Itm_Mtble": "budget_items_master",
        "PNR_Mtble": "pnr_master",
        "Sup_Mtbl": "suppliers_master",
        "Clnt_Mtbl": "clients_master",
        "Own_Mtbl": "owners_master",
        "Stff_Mtbl": "staff_master",
        # Transaction tables
        "Einv_TrxMtbl": "einv_transactions_master",
        "Bud_Pur_Trxtbl": "budget_purchase_transactions_master",
        "Bud_Sal_Trxtbl": "budget_sales_transactions_master",
    }
    return mapping.get(sheet_name)

# ============================================================
# MASTER DATA EXTRACTION
# ============================================================

def extract_master_data(source_file: str) -> Dict[str, Any]:
    results = {"tables_processed": 0, "records_inserted": 0, "errors": [], "details": {}}

    try:
        import pandas as pd
    except ImportError:
        results["errors"].append("pandas not installed: pip install pandas openpyxl")
        return results

    resolved = resolve_source_file(source_file)
    try:
        xls = pd.ExcelFile(resolved)
    except FileNotFoundError:
        results["errors"].append(f"File not found: {resolved}")
        return results
    except Exception as e:
        results["errors"].append(f"Error opening Excel: {str(e)}")
        return results

    batch_id = f"master_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    with get_db() as conn:
        for sheet_name in xls.sheet_names:
            table_name = _resolve_master_table(sheet_name)
            if not table_name:
                results["details"][sheet_name] = {"status": "SKIPPED", "reason": "No table mapping"}
                continue

            try:
                df = None
                header_row = 0
                for hr in range(3):
                    try:
                        df = pd.read_excel(xls, sheet_name=sheet_name, header=hr)
                        if len(df.columns) >= 2 and not all(str(c).startswith("Unnamed") for c in df.columns):
                            header_row = hr
                            break
                    except Exception:
                        continue

                if df is None or df.empty:
                    results["details"][sheet_name] = {"status": "EMPTY", "records": 0}
                    continue

                df.columns = [str(c).strip().replace(" ", "_").replace("-", "_") for c in df.columns]
                df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

                if df.empty:
                    results["details"][sheet_name] = {"status": "EMPTY_AFTER_CLEAN", "records": 0}
                    continue

                df["_extracted_at"] = datetime.now().isoformat()
                df["_source_file"] = source_file
                df["_batch_id"] = batch_id

                cols = df.columns.tolist()
                col_defs = ", ".join([f'"{c}" TEXT' for c in cols])
                create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" (id INTEGER PRIMARY KEY AUTOINCREMENT, {col_defs})'
                conn.execute(create_sql)

                placeholders = ", ".join(["?"] * len(cols))
                col_names = ", ".join([f'"{c}"' for c in cols])
                insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

                records = []
                for _, row in df.iterrows():
                    records.append(tuple(str(v) if pd.notna(v) else None for v in row.values))

                if records:
                    conn.executemany(insert_sql, records)
                    conn.commit()
                    results["tables_processed"] += 1
                    results["records_inserted"] += len(records)
                    results["details"][sheet_name] = {
                        "status": "SUCCESS", "records": len(records), "table": table_name, "header_row": header_row
                    }
                    logger.info(f"Master: {sheet_name} -> {table_name}: {len(records)} records")
                else:
                    results["details"][sheet_name] = {"status": "NO_RECORDS", "records": 0}

            except Exception as e:
                msg = f"{sheet_name}: {str(e)}"
                results["errors"].append(msg)
                logger.error(msg)
                continue

    return results

# ============================================================
# MODULE DATA EXTRACTION
# ============================================================

MODULE_CONFIG = {
    "BNK": {
        "source_file": "Data Base\\Bnk_TrnX_Sub_Key.xlsx",  # ← FIXED PATH
        "target_table": "bnk_staging",
        "col_map": {
            "Serial #": "transaction_id",
            "Check Book": "check_book_id",
            "Date": "transaction_date",
            "Narration": "narration",
            "Debit": "debit",
            "Credit": "credit",
        }
    },
    "SAL": {
        "source_file": "Sales_Data.xlsx",
        "target_table": "sales_staging",
        "col_map": {
            "Invoice_No": "invoice_no",
            "Invoice_Date": "invoice_date",
            "Client_ID": "client_id",
            "Amount": "amount",
            "Currency": "currency",
        }
    },
    "PUR": {
        "source_file": "Purchase_Data.xlsx",
        "target_table": "purchase_staging",
        "col_map": {
            "PO_No": "po_no",
            "PO_Date": "po_date",
            "Vendor_ID": "vendor_id",
            "Amount": "amount",
            "Currency": "currency",
        }
    },
    "EVN": {
        "source_file": "Events_Data.xlsx",
        "target_table": "events_staging",
        "col_map": {
            "PNR_ID": "pnr_id",
            "Event_Date": "event_date",
            "Client_ID": "client_id",
            "Gross_Sales": "gross_sales",
            "Currency": "currency",
        }
    },
    "ENV": {
        "source_file": "Environmental_Data.xlsx",
        "target_table": "environmental_staging",
        "col_map": {
            "Project_ID": "project_id",
            "Project_Date": "project_date",
            "Department": "department",
            "Amount": "amount",
            "Currency": "currency",
        }
    },
}

def extract_module_data(module: str, source_file: Optional[str] = None, dry_run: bool = True) -> Dict[str, Any]:
    try:
        import pandas as pd
    except ImportError:
        return {"status": "ERROR", "error": "pandas not installed"}

    config = MODULE_CONFIG.get(module)
    if not config:
        return {"status": "ERROR", "error": f"Unknown module: {module}"}

    file_path = resolve_source_file(source_file or config["source_file"])
    target_table = config["target_table"]
    col_map = config["col_map"]

    result = {
        "status": "SUCCESS", "module": module, "source_file": file_path,
        "target_table": target_table, "records_read": 0, "records_inserted": 0,
        "errors": [], "dry_run": dry_run,
    }

    try:
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        result["status"] = "ERROR"
        result["errors"].append(f"File not found: {file_path}")
        return result
    except Exception as e:
        result["status"] = "ERROR"
        result["errors"].append(f"Error reading Excel: {str(e)}")
        return result

    if df.empty:
        result["errors"].append("Excel file is empty")
        return result

    df.rename(columns=col_map, inplace=True)

    # ← FIXED: Use pd.Series default so fillna() works even if column missing
    if module == "BNK":
        debit_series = df.get("debit", pd.Series(0, index=df.index))
        credit_series = df.get("credit", pd.Series(0, index=df.index))
        df["amount"] = pd.to_numeric(debit_series, errors="coerce").fillna(0) - \
                       pd.to_numeric(credit_series, errors="coerce").fillna(0)
        df["currency"] = df.get("check_book_id", pd.Series("", index=df.index)).apply(
            lambda x: "USD" if "USD" in str(x).upper() else
                      "EUR" if "EUR" in str(x).upper() else
                      "GBP" if "GBP" in str(x).upper() else "EGP"
        )

    df["_extracted_at"] = datetime.now().isoformat()
    df["_batch_id"] = f"{module.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    df["_module"] = module

    result["records_read"] = len(df)

    if dry_run:
        result["preview"] = df.head(5).to_dict(orient="records")
        return result

    with get_db() as conn:
        try:
            if module == "BNK":
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS bnk_staging (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transaction_id TEXT, check_book_id TEXT, transaction_date TEXT,
                        narration TEXT, debit REAL, credit REAL, amount REAL, currency TEXT,
                        _extracted_at TEXT, _batch_id TEXT, _module TEXT
                    )
                """)
                insert_cols = ["transaction_id", "check_book_id", "transaction_date", "narration",
                               "debit", "credit", "amount", "currency", "_extracted_at", "_batch_id", "_module"]
            elif module == "SAL":
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sales_staging (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        invoice_no TEXT, invoice_date TEXT, client_id TEXT, amount REAL, currency TEXT,
                        _extracted_at TEXT, _batch_id TEXT, _module TEXT
                    )
                """)
                insert_cols = ["invoice_no", "invoice_date", "client_id", "amount", "currency",
                               "_extracted_at", "_batch_id", "_module"]
            elif module == "PUR":
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS purchase_staging (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        po_no TEXT, po_date TEXT, vendor_id TEXT, amount REAL, currency TEXT,
                        _extracted_at TEXT, _batch_id TEXT, _module TEXT
                    )
                """)
                insert_cols = ["po_no", "po_date", "vendor_id", "amount", "currency",
                               "_extracted_at", "_batch_id", "_module"]
            elif module == "EVN":
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS events_staging (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pnr_id TEXT, event_date TEXT, client_id TEXT, gross_sales REAL, currency TEXT,
                        _extracted_at TEXT, _batch_id TEXT, _module TEXT
                    )
                """)
                insert_cols = ["pnr_id", "event_date", "client_id", "gross_sales", "currency",
                               "_extracted_at", "_batch_id", "_module"]
            elif module == "ENV":
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS environmental_staging (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT, project_date TEXT, department TEXT, amount REAL, currency TEXT,
                        _extracted_at TEXT, _batch_id TEXT, _module TEXT
                    )
                """)
                insert_cols = ["project_id", "project_date", "department", "amount", "currency",
                               "_extracted_at", "_batch_id", "_module"]

            placeholders = ", ".join(["?"] * len(insert_cols))
            insert_sql = f"INSERT INTO {target_table} ({', '.join(insert_cols)}) VALUES ({placeholders})"

            records = []
            for _, row in df.iterrows():
                record = []
                for col in insert_cols:
                    val = row.get(col)
                    if pd.isna(val):
                        record.append(None)
                    elif col in ["transaction_id", "check_book_id", "narration", "invoice_no", "client_id",
                                 "currency", "po_no", "vendor_id", "pnr_id", "project_id", "department",
                                 "_extracted_at", "_batch_id", "_module"]:
                        record.append(str(val))
                    else:
                        record.append(float(val))
                records.append(tuple(record))

            conn.executemany(insert_sql, records)
            conn.commit()
            result["records_inserted"] = len(records)
            logger.info(f"Module: {module} -> {target_table}: {len(records)} records")

        except Exception as e:
            result["status"] = "ERROR"
            result["errors"].append(f"Database insert error: {str(e)}")
            logger.error(f"Insert error for {module}: {e}")

    return result

# ============================================================
# QUALITY SCORING
# ============================================================

def calculate_quality_score(module: str, batch_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        config = MODULE_CONFIG.get(module)
        if not config:
            return {"score": 0, "errors": ["Unknown module"]}

        table = config["target_table"]
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE _batch_id = ?", (batch_id,))
        total = cursor.fetchone()[0]

        if total == 0:
            return {"score": 0, "errors": ["No records found for batch"]}

        score = 95.0
        issues = []

        if module == "BNK":
            null_txn = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE _batch_id = ? AND transaction_id IS NULL", (batch_id,)).fetchone()[0]
            if null_txn > 0:
                score -= 10
                issues.append(f"{null_txn} records missing transaction_id")

            null_narr = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE _batch_id = ? AND narration IS NULL", (batch_id,)).fetchone()[0]
            if null_narr > 0:
                score -= 5
                issues.append(f"{null_narr} records missing narration")

            dupes = conn.execute(f"""
                SELECT transaction_id, COUNT(*) as cnt FROM {table}
                WHERE _batch_id = ? GROUP BY transaction_id HAVING cnt > 1
            """, (batch_id,)).fetchall()
            if dupes:
                score -= 10 * len(dupes)
                issues.append(f"{len(dupes)} duplicate transaction_ids")

        return {
            "score": max(0, score),
            "total_records": total,
            "issues": issues,
            "batch_id": batch_id
        }

if __name__ == "__main__":
    print("Extraction Engine v2.2.3 loaded.")
    print("Tables:", list(get_table_counts().keys()))