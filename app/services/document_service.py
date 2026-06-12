"""
Document Management System — Service Layer
Handles: USB scan, file copy, hash compute, auto-link, verification
"""

import hashlib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.documents import SupportingDocument, DocumentModule
from app.schemas.documents import IngestResultItem, VerifyResult


# ── Config ────────────────────────────────────────────
ARCHIVE_ROOT = Path(os.getenv("DOC_ARCHIVE_ROOT", r"D:\Data_Sources\docs"))
USB_ROOT_TEMPLATE = r"{drive}:\{base_path}"

# ── Auto-link patterns ──────────────────────────────
# Maps (module, function) → regex pattern for extracting transaction ID
AUTO_LINK_PATTERNS: Dict[Tuple[str, str], re.Pattern] = {
    ("Bank", "Statements"): re.compile(
        r"Bnk_(?P<account>[A-Za-z0-9]+)_(?P<date>\d{4}-\d{2})"
    ),
    ("Bank", "Transfers"): re.compile(r"TRX_(?P<id>\d+)"),
    ("Bank", "ATM"): re.compile(r"TRX_(?P<id>\d+)"),
    ("Sales", "Events"): re.compile(r"EVT_(?P<id>\d+)"),
    ("Sales", "Invoices"): re.compile(r"INV_(?P<id>\d+)"),
    ("Sales", "POs"): re.compile(r"PO_(?P<id>\d+)"),
    ("Purchase", "Orders"): re.compile(r"PO_(?P<id>\d+)"),
    ("Purchase", "Vendor_Invoices"): re.compile(r"VIN_(?P<id>\d+)"),
    ("Purchase", "Quotations"): re.compile(r"QUO_(?P<id>\d+)"),
    ("Purchase", "GRN"): re.compile(r"GRN_(?P<id>\d+)"),
    ("Events", "Work_Orders"): re.compile(r"WO_(?P<id>\d+)"),
    ("Events", "Staff_Assignments"): re.compile(r"SA_(?P<id>\d+)"),
    ("Events", "Line_Items"): re.compile(r"LI_(?P<id>\d+)"),
    ("E_Invoice", "Submissions"): re.compile(r"ETA_(?P<uuid>[a-f0-9-]+)"),
    ("E_Invoice", "QR_Codes"): re.compile(r"INV_(?P<id>\d+)"),
    ("Master_Data", "Clients"): re.compile(r"CLI_(?P<id>\d+)"),
    ("Master_Data", "Vendors"): re.compile(r"VND_(?P<id>\d+)"),
    ("Master_Data", "Items"): re.compile(r"ITM_(?P<id>\d+)"),
    ("HR", "Staff"): re.compile(r"STF_(?P<id>\d+)"),
    ("HR", "Owners"): re.compile(r"OWN_(?P<id>\d+)"),
    ("Costing", "Budget"): re.compile(r"BUD_(?P<id>\d+)"),
    ("Costing", "SCM"): re.compile(r"SCM_(?P<id>\d+)"),
    ("OR", "Analysis"): re.compile(r"OR_(?P<engine>[A-Z]+)_(?P<id>\d+)"),
    ("OR", "Reports"): re.compile(r"OR_(?P<engine>[A-Z]+)_(?P<id>\d+)"),
    ("Manufacturing", "Production"): re.compile(r"MFG_(?P<id>\d+)"),
    ("Manufacturing", "QC"): re.compile(r"QC_(?P<id>\d+)"),
}


class DocumentService:
    """Core document management operations."""

    def __init__(self, db: Session):
        self.db = db

    # ── Hash & File Ops ─────────────────────────────
    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def ensure_archive_dirs() -> None:
        """Create the full module/function folder tree if missing."""
        modules = [
            ("Bank", ["Statements", "Reconciliation", "Transfers", "ATM"]),
            ("Sales", ["Events", "Invoices", "POs", "Contracts"]),
            ("Purchase", ["Orders", "Vendor_Invoices", "Quotations", "GRN"]),
            ("Events", ["Work_Orders", "Staff_Assignments", "Line_Items"]),
            ("E_Invoice", ["Submissions", "QR_Codes", "Rejections"]),
            ("Master_Data", ["Clients", "Vendors", "Items"]),
            ("HR", ["Staff", "Owners"]),
            ("Costing", ["Budget", "SCM"]),
            ("OR", ["Analysis", "Reports"]),
            ("Manufacturing", ["Production", "QC"]),
        ]
        for module, functions in modules:
            for func in functions:
                path = ARCHIVE_ROOT / module / func
                path.mkdir(parents=True, exist_ok=True)

    # ── Ingest ────────────────────────────────────────
    def ingest_module(
        self,
        usb_drive: str,
        usb_base: str,
        module_name: str,
        auto_link: bool = True,
        copy_to_archive: bool = True,
        compute_hash: bool = True,
        uploaded_by: Optional[str] = None,
    ) -> List[IngestResultItem]:
        """Ingest all files from one USB module folder."""
        usb_root = Path(USB_ROOT_TEMPLATE.format(drive=usb_drive, base_path=usb_base))
        module_path = usb_root / module_name

        if not module_path.exists():
            return [
                IngestResultItem(
                    file=f"{module_name}/",
                    status="error",
                    reason=f"USB path not found: {module_path}",
                )
            ]

        results: List[IngestResultItem] = []
        doc_modules = (
            self.db.query(DocumentModule)
            .filter(DocumentModule.module_name == module_name)
            .all()
        )

        # Build function → transaction_table mapping
        func_to_table = {dm.function_name: dm.transaction_table for dm in doc_modules}

        for func_dir in module_path.iterdir():
            if not func_dir.is_dir():
                continue
            function_name = func_dir.name
            transaction_table = func_to_table.get(function_name)

            for file_path in func_dir.iterdir():
                if not file_path.is_file():
                    continue

                result = self._ingest_single_file(
                    file_path=file_path,
                    module_name=module_name,
                    function_name=function_name,
                    transaction_table=transaction_table,
                    auto_link=auto_link,
                    copy_to_archive=copy_to_archive,
                    compute_hash=compute_hash,
                    uploaded_by=uploaded_by,
                )
                results.append(result)

        return results

    def _ingest_single_file(
        self,
        file_path: Path,
        module_name: str,
        function_name: str,
        transaction_table: Optional[str],
        auto_link: bool,
        copy_to_archive: bool,
        compute_hash: bool,
        uploaded_by: Optional[str],
    ) -> IngestResultItem:
        """Ingest one file."""
        try:
            # Compute hash
            file_hash = self.compute_sha256(file_path) if compute_hash else ""
            file_size = file_path.stat().st_size

            # Determine archive path
            archive_dir = ARCHIVE_ROOT / module_name / function_name
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / file_path.name

            # Copy to archive
            if copy_to_archive:
                shutil.copy2(file_path, archive_path)

            # Auto-link: try to extract transaction ID from filename
            transaction_id = None
            link_status = "linked"
            link_reason = None

            if auto_link and transaction_table:
                pattern = AUTO_LINK_PATTERNS.get((module_name, function_name))
                if pattern:
                    match = pattern.search(file_path.stem)
                    if match:
                        # Use 'id' group if present, else first group
                        transaction_id = match.groupdict().get("id") or match.group(1)
                    else:
                        link_status = "orphaned"
                        link_reason = f"No pattern match for {file_path.name}"
                else:
                    link_status = "orphaned"
                    link_reason = (
                        f"No auto-link pattern for {module_name}/{function_name}"
                    )
            else:
                link_status = "orphaned"
                link_reason = "Auto-link disabled or no transaction table mapping"

            # Create DB record
            doc = SupportingDocument(
                module_name=module_name,
                function_name=function_name,
                transaction_table=transaction_table or "unknown",
                transaction_id=transaction_id or "orphaned",
                original_usb_path=str(file_path),
                archive_path=str(archive_path),
                file_hash_sha256=file_hash,
                file_size_bytes=file_size,
                file_name=file_path.name,
                file_ext=file_path.suffix.lstrip(".").lower(),
                status=link_status,
                uploaded_by=uploaded_by,
            )
            self.db.add(doc)
            self.db.commit()

            return IngestResultItem(
                file=f"{module_name}/{function_name}/{file_path.name}",
                status=link_status,
                reason=link_reason,
                transaction_id=transaction_id,
                archive_path=str(archive_path),
                file_hash=file_hash,
            )

        except Exception as e:
            return IngestResultItem(
                file=f"{module_name}/{function_name}/{file_path.name}",
                status="error",
                reason=str(e),
            )

    # ── Verify ────────────────────────────────────────
    def verify_archive(self, module_name: Optional[str] = None) -> VerifyResult:
        """Re-hash all archived files and update status."""
        query = self.db.query(SupportingDocument)
        if module_name:
            query = query.filter(SupportingDocument.module_name == module_name)

        docs = query.all()
        total = len(docs)
        verified = modified = missing = errors = 0

        for doc in docs:
            archive_path = Path(doc.archive_path)
            if not archive_path.exists():
                doc.status = "missing"
                missing += 1
                continue

            try:
                current_hash = self.compute_sha256(archive_path)
                if current_hash == doc.file_hash_sha256:
                    doc.status = "verified"
                    verified += 1
                else:
                    doc.status = "modified"
                    modified += 1
                doc.verified_at = datetime.utcnow()
            except Exception:
                errors += 1

        self.db.commit()
        return VerifyResult(
            total_checked=total,
            verified=verified,
            modified=modified,
            missing=missing,
            errors=errors,
        )

    # ── Query ─────────────────────────────────────────
    def get_by_transaction(self, table: str, txn_id: str) -> List[SupportingDocument]:
        return (
            self.db.query(SupportingDocument)
            .filter(
                SupportingDocument.transaction_table == table,
                SupportingDocument.transaction_id == txn_id,
            )
            .all()
        )

    def get_by_module(
        self, module: str, function: Optional[str] = None
    ) -> List[SupportingDocument]:
        q = self.db.query(SupportingDocument).filter(
            SupportingDocument.module_name == module
        )
        if function:
            q = q.filter(SupportingDocument.function_name == function)
        return q.all()

    def seed_document_modules(self) -> int:
        """Insert seed data into document_modules. Idempotent."""
        seed_data = [
            (
                "Bank",
                "Statements",
                "bnk_transactions",
                "Monthly bank statements",
                "Bnk_{account}_{date}.pdf",
            ),
            (
                "Bank",
                "Reconciliation",
                "bnk_reconciliation",
                "Reconciliation sheets",
                "Recon_{account}_{date}.xlsx",
            ),
            (
                "Bank",
                "Transfers",
                "bnk_transactions",
                "Transfer confirmations",
                "TRX_{id}_transfer.pdf",
            ),
            ("Bank", "ATM", "bnk_transactions", "ATM receipts", "TRX_{id}_atm.pdf"),
            ("Sales", "Events", "events", "Event documentation", "EVT_{id}_*.pdf"),
            ("Sales", "Invoices", "sales_invoices", "Sales invoices", "INV_{id}_*.pdf"),
            (
                "Sales",
                "POs",
                "purchase_orders",
                "Client purchase orders",
                "PO_{id}_client.pdf",
            ),
            (
                "Sales",
                "Contracts",
                "events",
                "Client contracts",
                "EVT_{id}_contract.pdf",
            ),
            (
                "Purchase",
                "Orders",
                "purchase_orders",
                "POs to suppliers",
                "PO_{id}_supplier.pdf",
            ),
            (
                "Purchase",
                "Vendor_Invoices",
                "vendor_invoices",
                "Supplier invoices",
                "VIN_{id}_*.pdf",
            ),
            (
                "Purchase",
                "Quotations",
                "purchase_orders",
                "Supplier quotations",
                "QUO_{id}_*.pdf",
            ),
            (
                "Purchase",
                "GRN",
                "purchase_orders",
                "Goods receipt notes",
                "GRN_{id}_*.pdf",
            ),
            (
                "Events",
                "Work_Orders",
                "work_orders",
                "WO documentation",
                "WO_{id}_*.pdf",
            ),
            (
                "Events",
                "Staff_Assignments",
                "staff_assignments",
                "Staff docs",
                "SA_{id}_*.pdf",
            ),
            (
                "Events",
                "Line_Items",
                "event_line_items",
                "Item delivery proof",
                "LI_{id}_*.pdf",
            ),
            (
                "E_Invoice",
                "Submissions",
                "sales_invoices",
                "ETA submission proof",
                "ETA_{uuid}.json",
            ),
            (
                "E_Invoice",
                "QR_Codes",
                "sales_invoices",
                "QR code images",
                "INV_{id}_qr.png",
            ),
            (
                "E_Invoice",
                "Rejections",
                "sales_invoices",
                "Rejection notices",
                "ETA_{uuid}_rej.json",
            ),
            ("Master_Data", "Clients", "clients", "KYC, tax cards", "CLI_{id}_*.pdf"),
            ("Master_Data", "Vendors", "vendors", "KYC, tax cards", "VND_{id}_*.pdf"),
            ("Master_Data", "Items", "items", "Spec sheets, images", "ITM_{id}_*.pdf"),
            ("HR", "Staff", "staff", "Contracts, IDs", "STF_{id}_*.pdf"),
            ("HR", "Owners", "owners", "Registration docs", "OWN_{id}_*.pdf"),
            (
                "Costing",
                "Budget",
                "budget_lines",
                "Budget approvals",
                "BUD_{id}_*.xlsx",
            ),
            ("Costing", "SCM", "scm_staging", "SCM analysis docs", "SCM_{id}_*.xlsx"),
            (
                "OR",
                "Analysis",
                "or_analyses",
                "OR engine outputs",
                "OR_{engine}_{id}.json",
            ),
            (
                "OR",
                "Reports",
                "or_analyses",
                "Generated reports",
                "OR_{engine}_{id}_report.pdf",
            ),
            (
                "Manufacturing",
                "Production",
                "mfg_orders",
                "Production orders",
                "MFG_{id}_*.pdf",
            ),
            ("Manufacturing", "QC", "mfg_orders", "Quality checks", "QC_{id}_*.pdf"),
        ]

        inserted = 0
        for row in seed_data:
            exists = (
                self.db.query(DocumentModule)
                .filter_by(module_name=row[0], function_name=row[1])
                .first()
            )
            if not exists:
                self.db.add(
                    DocumentModule(
                        module_name=row[0],
                        function_name=row[1],
                        transaction_table=row[2],
                        description=row[3],
                        filename_pattern=row[4],
                    )
                )
                inserted += 1
        self.db.commit()
        return inserted


async def run_nightly_verify():
    """Async wrapper for nightly archive verification. Scheduled via APScheduler."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        service = DocumentService(db)
        result = service.verify_archive()
        print(
            f"[{datetime.now()}] Document verify: {result.total_checked} checked, "
            f"{result.verified} verified, {result.modified} modified, "
            f"{result.missing} missing"
        )
    finally:
        db.close()
