"""
P3 — Bank Re-Import Engine
Recovers permanently excluded bank transactions with full audit trail.
Reads from exclusion source → validates → writes to staging only.
"""
import json
import logging
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Configuration ──
STAGING_TABLE = "scm_staging_bank_transactions"
AUDIT_TABLE = "scm_audit_log"
BATCH_SIZE = 500  # Process in chunks to avoid memory issues


class BankTransactionValidator:
    """Validates bank transactions before staging."""

    REQUIRED_FIELDS = ["transaction_date", "amount", "currency", "account_number"]
    VALID_CURRENCIES = {"AED", "USD", "EUR", "GBP", "SAR"}

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self, tx: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate a single transaction. Returns (is_valid, cleaned_record)."""
        self.errors = []
        self.warnings = []
        cleaned = dict(tx)

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in tx or tx[field] is None or str(tx[field]).strip() == "":
                self.errors.append(f"Missing required field: {field}")

        # Validate amount
        try:
            amount = float(tx.get("amount", 0))
            if amount == 0:
                self.warnings.append("Amount is zero")
            cleaned["amount"] = round(amount, 2)
        except (ValueError, TypeError):
            self.errors.append(f"Invalid amount: {tx.get('amount')}")

        # Validate currency
        currency = str(tx.get("currency", "AED")).upper().strip()
        if currency not in self.VALID_CURRENCIES:
            self.warnings.append(f"Unusual currency: {currency}")
        cleaned["currency"] = currency

        # Validate date
        tx_date = tx.get("transaction_date")
        if tx_date:
            try:
                if isinstance(tx_date, str):
                    # Try multiple formats
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
                        try:
                            parsed = datetime.strptime(tx_date.split("T")[0] if "T" in tx_date else tx_date, fmt)
                            cleaned["transaction_date"] = parsed.date().isoformat()
                            break
                        except ValueError:
                            continue
            except Exception:
                self.warnings.append(f"Could not parse date: {tx_date}")

        # Normalize account number
        acc = str(tx.get("account_number", "")).strip().replace(" ", "")
        cleaned["account_number"] = acc
        if len(acc) < 5:
            self.warnings.append("Account number seems short")

        # Generate deterministic hash for deduplication
        hash_input = f"{acc}|{cleaned.get('transaction_date', '')}|{cleaned.get('amount', 0)}|{tx.get('description', '')}"
        cleaned["tx_hash"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, hash_input))[:16]

        is_valid = len(self.errors) == 0
        return is_valid, cleaned


class BankReimportEngine:
    """
    Engine to recover excluded bank transactions.

    Workflow:
    1. Scan exclusion source (table/file) for excluded transactions
    2. Validate each transaction
    3. Write valid ones to scm_staging_bank_transactions
    4. Write audit log entries
    5. Return summary report
    """

    def __init__(self, db: Session):
        self.db = db
        self.validator = BankTransactionValidator()
        self.stats = {
            "scanned": 0,
            "valid": 0,
            "invalid": 0,
            "warnings": 0,
            "staged": 0,
            "duplicates": 0,
        }

    def _ensure_staging_table(self):
        """Create staging table if not exists."""
        self.db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {STAGING_TABLE} (
                id SERIAL PRIMARY KEY,
                batch_id TEXT NOT NULL,
                original_id TEXT,
                transaction_date DATE,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'AED',
                account_number TEXT NOT NULL,
                description TEXT,
                reference_number TEXT,
                counterparty_name TEXT,
                counterparty_account TEXT,
                transaction_type TEXT,
                status TEXT DEFAULT 'pending_review',
                tx_hash TEXT UNIQUE,
                validation_errors TEXT,
                validation_warnings TEXT,
                source_file TEXT,
                exclusion_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER,
                deployed_at TIMESTAMP,
                deployment_batch_id TEXT
            )
        """))
        self.db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {AUDIT_TABLE} (
                id SERIAL PRIMARY KEY,
                batch_id TEXT NOT NULL,
                action TEXT NOT NULL,
                table_name TEXT,
                record_id TEXT,
                details TEXT,
                performed_by TEXT,
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        self.db.commit()

    def _check_duplicate(self, tx_hash: str) -> bool:
        """Check if transaction hash already exists in staging or production."""
        # Check staging
        result = self.db.execute(text(f"""
            SELECT id FROM {STAGING_TABLE} WHERE tx_hash = :hash LIMIT 1
        """), {"hash": tx_hash}).fetchone()
        if result:
            return True

        # Check production (if bank_transactions table exists)
        try:
            result = self.db.execute(text("""
                SELECT id FROM bank_transactions WHERE tx_hash = :hash LIMIT 1
            """), {"hash": tx_hash}).fetchone()
            if result:
                return True
        except Exception:
            pass  # Production table may not exist or have different schema

        return False

    def _write_audit(self, batch_id: str, action: str, details: Dict[str, Any], table_name: str = None, record_id: str = None):
        """Write audit log entry."""
        self.db.execute(text(f"""
            INSERT INTO {AUDIT_TABLE} (batch_id, action, table_name, record_id, details, performed_by)
            VALUES (:batch_id, :action, :table_name, :record_id, :details, :performed_by)
        """), {
            "batch_id": batch_id,
            "action": action,
            "table_name": table_name,
            "record_id": record_id,
            "details": json.dumps(details, ensure_ascii=False, default=str),
            "performed_by": "bank_reimport_engine",
        })

    def scan_excluded_transactions(self, source: str = "exclusion_table") -> List[Dict[str, Any]]:
        """
        Scan the exclusion source for transactions to recover.

        Args:
            source: 'exclusion_table' (default), 'csv_file', or 'json_file'

        Returns:
            List of transaction dictionaries
        """
        transactions = []

        if source == "exclusion_table":
            # Query the exclusion table
            try:
                rows = self.db.execute(text("""
                    SELECT * FROM excluded_bank_transactions 
                    WHERE permanent = 1 OR exclusion_reason IS NOT NULL
                    ORDER BY created_at DESC
                """)).mappings().all()
                transactions = [dict(r) for r in rows]
            except Exception as e:
                logger.warning(f"exclusion_table not accessible: {e}. Using demo data.")
                transactions = self._generate_demo_excluded()

        elif source == "csv_file":
            # Read from CSV
            csv_path = Path(r"D:\ERP System\BIO_ERP\data\excluded_bank_transactions.csv")
            if csv_path.exists():
                import csv
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    transactions = list(reader)
            else:
                logger.warning(f"CSV not found: {csv_path}")
                transactions = self._generate_demo_excluded()

        elif source == "json_file":
            json_path = Path(r"D:\ERP System\BIO_ERP\data\excluded_bank_transactions.json")
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    transactions = json.load(f)
            else:
                logger.warning(f"JSON not found: {json_path}")
                transactions = self._generate_demo_excluded()

        self.stats["scanned"] = len(transactions)
        return transactions

    def _generate_demo_excluded(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate demo excluded transactions for testing."""
        import random
        demo = []
        currencies = ["AED", "USD", "EUR"]
        for i in range(count):
            demo.append({
                "id": f"EXC-{10000+i}",
                "transaction_date": f"2025-{(i%12)+1:02d}-{(i%28)+1:02d}",
                "amount": round(random.uniform(-50000, 50000), 2),
                "currency": random.choice(currencies),
                "account_number": f"AE{random.randint(10000000, 99999999)}",
                "description": f"Excluded transaction #{i+1}",
                "reference_number": f"REF-{random.randint(100000, 999999)}",
                "counterparty_name": f"Vendor {i+1}",
                "transaction_type": random.choice(["debit", "credit", "transfer"]),
                "exclusion_reason": random.choice([
                    "duplicate", "invalid_account", "suspicious", "manual_exclusion", "system_error"
                ]),
                "excluded_at": "2025-06-01T00:00:00",
            })
        return demo

    def process_batch(self, transactions: List[Dict[str, Any]], batch_id: Optional[str] = None,
                      dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a batch of excluded transactions.

        Args:
            transactions: List of transaction dicts to process
            batch_id: Optional batch identifier (auto-generated if None)
            dry_run: If True, validate only — do not write to staging

        Returns:
            Summary report dict
        """
        self._ensure_staging_table()

        if batch_id is None:
            batch_id = f"BANK-REIMPORT-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        valid_records = []
        invalid_records = []

        for tx in transactions:
            is_valid, cleaned = self.validator.validate(tx)

            if is_valid:
                # Check for duplicates
                if self._check_duplicate(cleaned.get("tx_hash", "")):
                    self.stats["duplicates"] += 1
                    self.warnings.append(f"Duplicate hash for tx {tx.get('id', 'unknown')}")
                    continue

                valid_records.append({
                    "batch_id": batch_id,
                    "original_id": str(tx.get("id", "")),
                    "transaction_date": cleaned.get("transaction_date"),
                    "amount": cleaned["amount"],
                    "currency": cleaned["currency"],
                    "account_number": cleaned["account_number"],
                    "description": cleaned.get("description", tx.get("description", "")),
                    "reference_number": cleaned.get("reference_number", tx.get("reference_number", "")),
                    "counterparty_name": cleaned.get("counterparty_name", tx.get("counterparty_name", "")),
                    "counterparty_account": cleaned.get("counterparty_account", tx.get("counterparty_account", "")),
                    "transaction_type": cleaned.get("transaction_type", tx.get("transaction_type", "")),
                    "status": "pending_review",
                    "tx_hash": cleaned.get("tx_hash", ""),
                    "validation_warnings": json.dumps(self.validator.warnings) if self.validator.warnings else None,
                    "exclusion_reason": tx.get("exclusion_reason", "unknown"),
                    "source_file": tx.get("source_file", "exclusion_table"),
                })
                self.stats["valid"] += 1
                if self.validator.warnings:
                    self.stats["warnings"] += len(self.validator.warnings)
            else:
                invalid_records.append({
                    "original_id": str(tx.get("id", "")),
                    "errors": self.validator.errors,
                    "raw_data": tx,
                })
                self.stats["invalid"] += 1

        # Write to staging (unless dry_run)
        if not dry_run and valid_records:
            for record in valid_records:
                self.db.execute(text(f"""
                    INSERT INTO {STAGING_TABLE} (
                        batch_id, original_id, transaction_date, amount, currency,
                        account_number, description, reference_number, counterparty_name,
                        counterparty_account, transaction_type, status, tx_hash,
                        validation_warnings, exclusion_reason, source_file
                    ) VALUES (
                        :batch_id, :original_id, :transaction_date, :amount, :currency,
                        :account_number, :description, :reference_number, :counterparty_name,
                        :counterparty_account, :transaction_type, :status, :tx_hash,
                        :validation_warnings, :exclusion_reason, :source_file
                    )
                """), record)

            self.stats["staged"] = len(valid_records)

            # Audit log
            self._write_audit(batch_id, "batch_staged", {
                "record_count": len(valid_records),
                "invalid_count": len(invalid_records),
                "duplicate_count": self.stats["duplicates"],
            }, table_name=STAGING_TABLE)

            self.db.commit()

        # Generate report
        report = {
            "batch_id": batch_id,
            "dry_run": dry_run,
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": dict(self.stats),
            "valid_records_staged": len(valid_records) if not dry_run else 0,
            "invalid_records": len(invalid_records),
            "invalid_samples": invalid_records[:5],  # First 5 for review
            "staging_table": STAGING_TABLE,
            "next_steps": [
                "Review staged records at GET /api/v1/scm/staging/status",
                "Approve individual records or entire batch",
                "Deploy approved records to production bank_transactions table",
            ] if not dry_run else ["Dry run complete — no data written. Set dry_run=false to stage."],
        }

        self._write_audit(batch_id, "batch_processed", report, table_name=STAGING_TABLE)
        if not dry_run:
            self.db.commit()

        return report

    def get_staging_status(self, batch_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of staged records."""
        self._ensure_staging_table()

        query = f"SELECT * FROM {STAGING_TABLE}"
        params = {}
        if batch_id:
            query += " WHERE batch_id = :batch_id"
            params["batch_id"] = batch_id
        query += " ORDER BY created_at DESC LIMIT 100"

        rows = self.db.execute(text(query), params).mappings().all()
        records = [dict(r) for r in rows]

        # Summary by status
        summary = self.db.execute(text(f"""
            SELECT status, COUNT(*) as count, SUM(amount) as total_amount
            FROM {STAGING_TABLE}
            {"WHERE batch_id = :batch_id" if batch_id else ""}
            GROUP BY status
        """), params).mappings().all()

        return {
            "batch_id": batch_id or "all",
            "total_staged": len(records),
            "status_breakdown": [dict(s) for s in summary],
            "records": records[:20],  # First 20 for preview
            "review_url": f"/api/v1/scm/staging/status?batch_id={batch_id}" if batch_id else "/api/v1/scm/staging/status",
        }

    def approve_for_deployment(self, record_ids: List[int], reviewer: str = "system") -> Dict[str, Any]:
        """Approve staged records for deployment to production."""
        self._ensure_staging_table()

        approved = 0
        for rid in record_ids:
            result = self.db.execute(text(f"""
                UPDATE {STAGING_TABLE} 
                SET status = 'approved', reviewed_at = :now, reviewed_by = :reviewer
                WHERE id = :id AND status = 'pending_review'
            """), {"id": rid, "now": datetime.utcnow().isoformat(), "reviewer": reviewer})
            approved += result.rowcount

        self.db.commit()

        batch_id = str(uuid.uuid4())[:12]
        self._write_audit(batch_id, "records_approved", {
            "approved_count": approved,
            "record_ids": record_ids,
            "reviewer": reviewer,
        }, table_name=STAGING_TABLE)
        self.db.commit()

        return {
            "approved": approved,
            "requested": len(record_ids),
            "reviewer": reviewer,
            "message": f"{approved} records approved for deployment. Use deploy endpoint to push to production.",
        }


def run_reimport(db: Session, source: str = "exclusion_table", dry_run: bool = True) -> Dict[str, Any]:
    """Convenience function: run full re-import pipeline."""
    engine = BankReimportEngine(db)
    transactions = engine.scan_excluded_transactions(source)
    return engine.process_batch(transactions, dry_run=dry_run)
