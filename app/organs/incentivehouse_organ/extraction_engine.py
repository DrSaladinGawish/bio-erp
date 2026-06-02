"""
Extraction Engine v2.1 — Real data extraction from Excel/CSV into staging tables.
Handles master data (multi-sheet), bank transactions, and all 5 ERP modules.
"""

import sqlite3
import json
import logging
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from contextlib import contextmanager
from io import StringIO

logger = logging.getLogger("extraction_engine")

BATCH_ID = f"BATCH-{uuid.uuid4().hex[:12].upper()}"

STAGING_TABLES = {
    "BNK": "bnk_staging",
    "SAL": "sal_staging",
    "PUR": "pur_staging",
    "EVN": "evn_staging",
    "ENV": "env_staging",
}

MASTER_TABLE_SCHEMAS = {
    "coa_master": ["acc_key", "acc_name", "acc_type", "parent_key"],
    "client_master": ["clnt_id", "clnt_name", "clnt_type", "branch", "status"],
    "vendor_master": ["ven_id", "ven_name", "ven_type", "status"],
    "staff_master": ["stf_code", "stf_name", "stf_role", "status"],
}


@contextmanager
def get_db(db_path: str):
    conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def detect_file_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in (".xlsx", ".xls", ".xlsm"):
        return "excel"
    elif ext == ".csv":
        return "csv"
    elif ext == ".mdb" or ext == ".accdb":
        return "access"
    return "unknown"


def _safe_str(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val) -> int:
    if val is None:
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _detect_column(df, candidates):
    """Find a column in dataframe matching any candidate (case-insensitive, partial match)."""
    cols = {c.strip().upper().replace(" ", "_").replace(".", "").replace("#", ""): c for c in df.columns}
    for cand in candidates:
        key = cand.upper().replace(" ", "_").replace(".", "").replace("#", "")
        if key in cols:
            return cols[key]
        for col_key, orig in cols.items():
            if key in col_key or col_key in key:
                return orig
    return None


def _normalize_columns(df):
    """Normalize column names to uppercase with underscores."""
    df = df.copy()
    mapping = {}
    for c in df.columns:
        norm = str(c).strip().replace(" ", "_").replace(".", "").replace("#", "").replace("/", "_").upper()
        mapping[c] = norm
    df.rename(columns=mapping, inplace=True)
    return df


# ── Master Data Extraction ──

def _load_sheet_auto_header(xl, sheet_name: str):
    """Load a sheet with auto header detection for master data."""
    import pandas as pd
    for header_row in range(5):
        try:
            df = pd.read_excel(xl, sheet_name=sheet_name, header=header_row, dtype=str)
            unnamed = [c for c in df.columns if "Unnamed" in str(c)]
            if df.shape[1] >= 2 and df.shape[0] > 0 and len(unnamed) < df.shape[1]:
                return df
        except Exception:
            continue
    return pd.read_excel(xl, sheet_name=sheet_name, dtype=str)

def extract_master_data(db_path: str, excel_path: str, user: str = "system") -> Dict[str, Any]:
    """
    Extract master data from a multi-sheet Excel workbook.
    Each sheet name maps to a table name. Columns are auto-detected and mapped.
    """
    import pandas as pd

    results = {"tables_processed": 0, "records_inserted": 0, "errors": [], "warnings": []}

    try:
        xl = pd.ExcelFile(excel_path, engine="openpyxl")
    except Exception as e:
        results["errors"].append(f"Failed to open Excel file '{excel_path}': {e}")
        return results

    for sheet_name in xl.sheet_names:
        sheet_clean = sheet_name.strip().lower().replace(" ", "_")
        try:
            df = _load_sheet_auto_header(xl, sheet_name)
            if df.empty:
                results["warnings"].append(f"Sheet '{sheet_name}' is empty, skipped")
                continue

            df = _normalize_columns(df)
            df = df.where(pd.notna(df), None)

            # Determine target table
            target_table = _resolve_master_table(sheet_clean, df)

            if not target_table:
                results["warnings"].append(f"Could not map sheet '{sheet_name}' to a table, skipped")
                continue

            count = _insert_master_data(db_path, target_table, df, excel_path)
            results["tables_processed"] += 1
            results["records_inserted"] += count
            logger.info(f"[Master] {sheet_name} -> {target_table}: {count} records")

        except Exception as e:
            err = f"Sheet '{sheet_name}': {str(e)}"
            results["errors"].append(err)
            logger.error(f"[Master] Error on sheet '{sheet_name}': {e}")

    return results


def _resolve_master_table(sheet_name: str, df) -> Optional[str]:
    """Map sheet name or its columns to a known master table."""
    name_aliases = {
        "coa_mtbl": "coa_master", "coa_mtble": "coa_master",
        "clnt_mtbl": "client_master", "clnt_mtble": "client_master",
        "sup_mtbl": "vendor_master", "ven_mtbl": "vendor_master", "vendor_mtbl": "vendor_master",
        "stff_mtbl": "staff_master", "staff_mtbl": "staff_master", "stf_mtbl": "staff_master",
    }

    if sheet_name in name_aliases:
        return name_aliases[sheet_name]

    # Direct name match
    if sheet_name in MASTER_TABLE_SCHEMAS:
        return sheet_name

    # Fuzzy name match
    for table_name in MASTER_TABLE_SCHEMAS:
        if table_name.replace("_", "") in sheet_name.replace("_", ""):
            return table_name
        if sheet_name.replace("_", "") in table_name.replace("_", ""):
            return table_name

    # Column-based detection
    all_cols = [c.upper().replace(" ", "").replace("-", "") for c in df.columns]
    for table_name, schema in MASTER_TABLE_SCHEMAS.items():
        required = [c.upper().replace(" ", "").replace("-", "") for c in schema]
        match_score = sum(1 for r in required if any(r in c or c in r for c in all_cols))
        if match_score >= 2:
            return table_name

    return None


def _insert_master_data(db_path: str, table: str, df, source_file: str) -> int:
    """Insert master data rows into the target table, mapping columns dynamically."""
    schema = MASTER_TABLE_SCHEMAS.get(table, [])
    if not schema:
        return 0

    col_map = {}
    for s_col in schema:
        candidates = [
            s_col,
            s_col.replace("_", ""),
            s_col.upper(),
        ]
        mapped = _detect_column(df, candidates)
        if mapped:
            col_map[s_col] = mapped

    if not col_map:
        return 0

    cols = list(col_map.keys())
    placeholders = ",".join("?" for _ in cols)
    sql = f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({placeholders})"

    with get_db(db_path) as conn:
        count = 0
        for _, row in df.iterrows():
            values = [row.get(col_map[c], None) for c in cols]
            try:
                conn.execute(sql, values)
                count += 1
            except Exception:
                pass
        conn.commit()

    return count


# ── Bank Transaction Extraction ──

def extract_bank_transactions(db_path: str, excel_path: str, module: str,
                               user: str = "system", dry_run: bool = False) -> Dict[str, Any]:
    """
    Extract bank transactions from Excel into bnk_staging.
    Handles column detection, currency inference, amount calculation.
    """
    import pandas as pd

    result = {
        "records_read": 0,
        "records_extracted": 0,
        "errors": [],
        "warnings": [],
    }

    try:
        df = _load_excel_with_header_detection(excel_path)
    except Exception as e:
        result["errors"].append(f"Failed to load Excel: {e}")
        return result

    df = _normalize_columns(df)
    df = df.where(pd.notna(df), None)
    result["records_read"] = len(df)

    # Map columns
    date_col = _detect_column(df, ["DATE", "TRANSACTION_DATE", "TRNX_DATE", "T_DATE", "VALUE_DATE", "POSTING_DATE"])
    desc_col = _detect_column(df, ["DESCRIPTION", "NARRATION", "DETAILS", "REMARKS", "PARTICULARS", "MEMO"])
    debit_col = _detect_column(df, ["DEBIT", "DR", "DEBIT_AMOUNT", "OUTFLOW", "WITHDRAWAL", "PAYMENT"])
    credit_col = _detect_column(df, ["CREDIT", "CR", "CREDIT_AMOUNT", "INFLOW", "DEPOSIT", "RECEIPT"])
    amt_col = _detect_column(df, ["AMOUNT", "AMT", "VALUE", "TRANSACTION_AMOUNT", "SUM"])
    curr_col = _detect_column(df, ["CURRENCY", "CCY", "CUR", "CURR"])
    ref_col = _detect_column(df, ["TRNX_NUM", "TRANSACTION_NUM", "TRANSACTION_NO", "TRANSACTION_ID", "REFERENCE", "REF", "TRANS_ID", "VOUCHER", "CHEQUE_NO", "CHEQUE", "TRNX_REF"])
    serial_col = _detect_column(df, ["SERIAL", "SERIAL_NUMBER", "SERIAL_NO", "ID", "TRANSACTION_NO"])
    check_book_col = _detect_column(df, ["CHECK_BOOK", "CHECK_BOOK_ID", "ACCOUNT", "BANK_ACCOUNT", "CB"])

    table = STAGING_TABLES.get(module, "bnk_staging")
    rows_inserted = 0
    now = datetime.now().isoformat()

    stmt = f"""
        INSERT INTO {table}
        (transaction_id, transaction_date, description, amount_egp, amount_orig,
         currency, sub_led_code, pnr_id, validation_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PASS', ?)
    """

    if not dry_run:
        with get_db(db_path) as conn:
            for idx, row in df.iterrows():
                try:
                    tid = _safe_str(row.get(ref_col)) if ref_col else f"{module}_{idx+1:08d}"
                    if serial_col:
                        tid = tid or _safe_str(row.get(serial_col))
                    tdate = _safe_str(row.get(date_col)) if date_col else ""
                    desc = _safe_str(row.get(desc_col)) if desc_col else ""

                    debit = _safe_float(row.get(debit_col)) if debit_col else 0.0
                    credit = _safe_float(row.get(credit_col)) if credit_col else 0.0
                    amount = _safe_float(row.get(amt_col)) if amt_col else 0.0
                    if amount == 0.0 and (debit_col or credit_col):
                        amount = debit - credit

                    if amount == 0.0 and amt_col is None and debit_col is None and credit_col is None:
                        continue

                    curr = _safe_str(row.get(curr_col)).upper() if curr_col else "EGP"
                    if not curr:
                        curr = "EGP"

                    conn.execute(stmt, (
                        tid, tdate, desc, abs(amount), amount,
                        curr, "", "", now
                    ))
                    rows_inserted += 1
                except Exception as e:
                    result["errors"].append(f"Row {idx+1}: {e}")
                    if len(result["errors"]) > 100:
                        result["errors"].append("... too many errors, truncating")
                        break

            conn.commit()
    else:
        rows_inserted = len(df)

    result["records_extracted"] = rows_inserted
    return result


def _load_excel_with_header_detection(path: str):
    """Load Excel file, auto-detecting the header row."""
    import pandas as pd
    xl = pd.ExcelFile(path, engine="openpyxl")
    sheet = xl.sheet_names[0]

    for header_row in range(5):
        try:
            df = pd.read_excel(xl, sheet_name=sheet, header=header_row)
            if len(df.columns) >= 3 and len(df) > 0:
                return df
        except Exception:
            continue
    return pd.read_excel(xl, sheet_name=sheet)


# ── Generic Module Extraction ──

def extract_module_data(db_path: str, excel_path: str, module: str,
                         user: str = "system", dry_run: bool = False) -> Dict[str, Any]:
    """
    Generic extraction for any module (BNK, SAL, PUR, EVN, ENV).
    BNK uses bank-specific extraction; others use a generic column-mapped approach.
    """
    if module == "BNK":
        return extract_bank_transactions(db_path, excel_path, module, user, dry_run)

    import pandas as pd

    result = {"records_read": 0, "records_extracted": 0, "errors": [], "warnings": []}
    table = STAGING_TABLES.get(module)
    if not table:
        result["errors"].append(f"Unknown module: {module}")
        return result

    try:
        df = _load_excel_with_header_detection(excel_path)
    except Exception as e:
        result["errors"].append(f"Failed to load: {e}")
        return result

    df = _normalize_columns(df)
    df = df.where(pd.notna(df), None)
    result["records_read"] = len(df)

    # Common column mapping
    date_col = _detect_column(df, ["DATE", "TRANSACTION_DATE", "TRNX_DATE", "T_DATE", "INVOICE_DATE"])
    desc_col = _detect_column(df, ["DESCRIPTION", "NARRATION", "DETAILS", "PARTICULARS", "REMARKS"])
    amt_col = _detect_column(df, ["AMOUNT", "AMT", "VALUE", "TOTAL", "SUM", "PRICE", "AMOUNT_EGP"])
    curr_col = _detect_column(df, ["CURRENCY", "CCY", "CUR"])
    ref_col = _detect_column(df, ["REFERENCE", "REF", "TRANSACTION_ID", "ID", "VOUCHER", "INVOICE_NO", "PO_NO"])
    client_col = _detect_column(df, ["CLIENT", "CLIENT_ID", "CLIENT_NAME", "CUSTOMER", "CUSTOMER_ID"])
    vendor_col = _detect_column(df, ["VENDOR", "VENDOR_ID", "VENDOR_NAME", "SUPPLIER", "SUPPLIER_ID"])

    now = datetime.now().isoformat()

    if module == "SAL":
        stmt = f"""INSERT INTO {table} (invoice_no, client_id, amount, currency, trnx_date, description, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)"""
    elif module == "PUR":
        stmt = f"""INSERT INTO {table} (po_no, vendor_id, amount, currency, trnx_date, description, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)"""
    elif module == "EVN":
        stmt = f"""INSERT INTO {table} (pnr_id, client_id, client_name, currency_id, event_description,
                   start_date, end_date, gross_sales, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'STAGED', ?)"""
    elif module == "ENV":
        stmt = f"""INSERT INTO {table} (created_at) VALUES (?)"""
    else:
        result["errors"].append(f"Unsupported module: {module}")
        return result

    rows_inserted = 0

    if not dry_run:
        with get_db(db_path) as conn:
            for idx, row in df.iterrows():
                try:
                    rows_inserted += 1
                    tdate = _safe_str(row.get(date_col)) if date_col else ""
                    desc = _safe_str(row.get(desc_col)) if desc_col else ""
                    amt = _safe_float(row.get(amt_col)) if amt_col else 0.0
                    curr = _safe_str(row.get(curr_col)).upper() if curr_col else "EGP"

                    if module == "SAL":
                        inv = _safe_str(row.get(ref_col)) if ref_col else f"SAL_{idx+1:08d}"
                        cid = _safe_str(row.get(client_col)) if client_col else ""
                        conn.execute(stmt, (inv, cid, amt, curr, tdate, desc, now))
                    elif module == "PUR":
                        po = _safe_str(row.get(ref_col)) if ref_col else f"PUR_{idx+1:08d}"
                        vid = _safe_str(row.get(vendor_col)) if vendor_col else ""
                        conn.execute(stmt, (po, vid, amt, curr, tdate, desc, now))
                    elif module == "EVN":
                        pnr = _safe_str(row.get(ref_col)) if ref_col else f"EVN_{idx+1:08d}"
                        cid = _safe_str(row.get(client_col)) if client_col else ""
                        cname = _safe_str(row.get(_detect_column(df, ["CLIENT_NAME", "CLIENT", "CUSTOMER_NAME"]))) or ""
                        ccy_id = _safe_str(row.get(curr_col)) if curr_col else "EGP"
                        sdate = tdate
                        edate = tdate
                        gsales = amt
                        conn.execute(stmt, (pnr, cid, cname, ccy_id, desc, sdate, edate, gsales, now))
                    elif module == "ENV":
                        conn.execute(stmt, (now,))
                except Exception as e:
                    result["errors"].append(f"Row {idx+1}: {e}")
            conn.commit()

    result["records_extracted"] = rows_inserted if not dry_run else len(df)
    return result


# ── Count records in staging ──

def get_table_counts(db_path: str) -> Dict[str, int]:
    """Return record counts for all staging and master tables."""
    tables = [
        "bnk_staging", "sal_staging", "pur_staging", "evn_staging", "env_staging",
        "extraction_log", "validation_log", "staging_log", "reconcile_log",
        "approval_log", "promotion_log", "observe_log",
        "coa_master", "client_master", "vendor_master", "staff_master",
    ]
    counts = {}
    with get_db(db_path) as conn:
        for t in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) as cnt FROM {t}").fetchone()
                counts[t] = row["cnt"]
            except Exception:
                counts[t] = 0
    return counts
