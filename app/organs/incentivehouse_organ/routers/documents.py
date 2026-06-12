"""Document Management System Router — IHE organ level."""

import hashlib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.organs.incentivehouse_organ.db import get_db

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

_ARCHIVE_ROOT = Path(
    os.getenv("IH_DOC_ARCHIVE", str(Path(__file__).parent.parent / "archive"))
)


# ── Pydantic schemas ─────────────────────────────────
class DocumentOut(BaseModel):
    id: str
    module_name: str
    function_name: str
    transaction_table: str
    transaction_id: str
    original_usb_path: Optional[str] = None
    archive_path: str
    file_hash_sha256: str
    file_size_bytes: int
    file_name: str
    file_ext: str
    ingested_at: Optional[str] = None
    verified_at: Optional[str] = None
    status: str
    uploaded_by: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    total: int
    items: list


class DocumentModuleOut(BaseModel):
    module_name: str
    function_name: str
    transaction_table: str
    description: Optional[str] = None
    filename_pattern: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentModuleList(BaseModel):
    modules: list


class IngestRequest(BaseModel):
    usb_drive_letter: str = Field(default="D", pattern=r"^[A-Za-z]$")
    usb_base_path: str = "flash memory\\USB Drive"
    modules: list[str] = []
    auto_link: bool = True
    copy_to_archive: bool = True
    compute_hash: bool = True


class IngestResultItem(BaseModel):
    file: str
    status: str
    reason: Optional[str] = None
    transaction_id: Optional[str] = None
    archive_path: Optional[str] = None
    file_hash: Optional[str] = None


class IngestResponse(BaseModel):
    total_files_found: int
    ingested: int
    linked: int
    orphaned: int
    errors: int
    bytes_copied: int
    manifest: list[IngestResultItem]


class VerifyRequest(BaseModel):
    module_name: Optional[str] = None


class VerifyResult(BaseModel):
    total_checked: int
    verified: int
    modified: int
    missing: int
    errors: int


class LinkRequest(BaseModel):
    document_id: str
    transaction_table: str
    transaction_id: str


# ── Helpers ──────────────────────────────────────────


def _compute_file_hash(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _match_module(filename: str, modules: list[dict]) -> Optional[dict]:
    """Match a filename against document_modules patterns to determine module info."""
    for mod in modules:
        pattern = mod.get("filename_pattern") or ""
        if not pattern:
            continue
        rx = pattern.replace("{id}", r"[\w-]+").replace("{uuid}", r"[\w-]+")
        rx = rx.replace("{account}", r"[\w\s]+").replace("{date}", r"[\d-]+")
        rx = rx.replace("{engine}", r"[\w-]+")
        rx = rx.replace("*", r".*")
        try:
            if re.search(rx, filename, re.IGNORECASE):
                return mod
        except re.error:
            continue
    return None


def _extract_id_from_filename(filename: str, pattern: str) -> Optional[str]:
    """Extract the transaction ID from a filename matching a pattern.
    Looks for {id}, {uuid}, {engine} placeholders and extracts captured values."""
    if "{id}" in pattern or "{uuid}" in pattern:
        rx = pattern.replace("{engine}", r"([\w-]+)").replace("{uuid}", r"([\w-]+)")
        rx = rx.replace("{id}", r"([\w-]+)").replace("{account}", r"([\w\s]+)")
        rx = rx.replace("{date}", r"([\d-]+)").replace("*", r".*")
        m = re.search(rx, filename, re.IGNORECASE)
        if m:
            for group in m.groups():
                if group:
                    return group
    return None


def _attempt_auto_link(
    db: Session, transaction_table: str, extracted_id: str
) -> Optional[str]:
    """Try to find a matching record in the transaction table."""
    if not extracted_id or not transaction_table:
        return None
    try:
        row = db.execute(
            text(f"SELECT id FROM {transaction_table} WHERE id = :id LIMIT 1"),
            {"id": extracted_id},
        ).fetchone()
        if row:
            return str(row[0])
    except Exception:
        pass
    return None


# ── Ingest ───────────────────────────────────────────
@router.post("/ingest", response_model=IngestResponse)
def ingest_documents(req: IngestRequest, db: Session = Depends(get_db)):
    # If usb_base_path looks like an absolute path (e.g. "C:\\..." or starts with /),
    # use it directly; otherwise construct from drive letter + base path
    if req.usb_base_path and (
        len(req.usb_base_path) > 1
        and req.usb_base_path[1] == ":"
        or req.usb_base_path.startswith("/")
        or req.usb_base_path.startswith("\\")
    ):
        base_path = Path(req.usb_base_path).resolve()
        usb_root = base_path
    else:
        usb_root = Path(f"{req.usb_drive_letter}:\\").resolve()
        base_path = usb_root / req.usb_base_path

    if not base_path.exists():
        raise HTTPException(status_code=400, detail=f"USB path not found: {base_path}")

    # Load module configs for pattern matching
    raw_modules = db.execute(text("SELECT * FROM document_modules")).fetchall()
    modules = [dict(r._mapping) for r in raw_modules]
    if req.modules:
        modules = [m for m in modules if m["module_name"] in req.modules]

    # Scan for files
    all_files = [p for p in base_path.rglob("*") if p.is_file()]
    total_found = len(all_files)

    manifest: list[dict] = []
    ingested = 0
    linked = 0
    orphaned = 0
    errors = 0
    bytes_copied = 0

    for fpath in all_files:
        fname = fpath.name
        ext = fpath.suffix.lstrip(".").lower()
        item: dict = {
            "file": str(fpath.relative_to(usb_root)),
            "status": "error",
            "reason": None,
        }

        try:
            file_hash = _compute_file_hash(fpath) if req.compute_hash else ""
            file_size = fpath.stat().st_size

            # Check for duplicate by hash
            existing = db.execute(
                text(
                    "SELECT id FROM supporting_documents WHERE file_hash_sha256 = :h LIMIT 1"
                ),
                {"h": file_hash},
            ).fetchone()

            if existing:
                item.update(
                    {
                        "status": "skipped",
                        "reason": "duplicate hash",
                        "file_hash": file_hash,
                    }
                )
                manifest.append(item)
                continue

            # Match filename against module patterns
            matched = _match_module(fname, modules)

            module_name = matched["module_name"] if matched else "Unknown"
            function_name = matched["function_name"] if matched else "Uncategorised"
            transaction_table = matched["transaction_table"] if matched else ""
            transaction_id = ""

            if matched:
                extracted_id = _extract_id_from_filename(
                    fname, matched.get("filename_pattern", "")
                )
                if extracted_id and req.auto_link:
                    linked_id = _attempt_auto_link(db, transaction_table, extracted_id)
                    if linked_id:
                        transaction_id = linked_id
                        linked += 1
                    else:
                        # Store the extracted ID anyway for manual linking later
                        transaction_id = extracted_id
                elif extracted_id:
                    transaction_id = extracted_id

            archive_subdir = _ARCHIVE_ROOT / module_name / function_name
            archive_subdir.mkdir(parents=True, exist_ok=True)
            dest = archive_subdir / fname

            # Avoid name collision
            if dest.exists():
                stem = dest.stem
                dest = (
                    archive_subdir
                    / f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{dest.suffix}"
                )

            if req.copy_to_archive:
                shutil.copy2(str(fpath), str(dest))
                bytes_copied += file_size

            # Absolute path stored in DB for portability
            archive_path = str(dest.resolve())

            db.execute(
                text("""INSERT INTO supporting_documents
                    (module_name, function_name, transaction_table, transaction_id,
                     original_usb_path, archive_path, file_hash_sha256, file_size_bytes,
                     file_name, file_ext, status, ingested_at)
                    VALUES (:mn, :fn, :tt, :tid, :usb, :arch, :hash, :sz, :fnm, :ext, 'linked', :now)"""),
                {
                    "mn": module_name,
                    "fn": function_name,
                    "tt": transaction_table,
                    "tid": transaction_id,
                    "usb": str(fpath),
                    "arch": archive_path,
                    "hash": file_hash,
                    "sz": file_size,
                    "fnm": fname,
                    "ext": ext,
                    "now": datetime.now().isoformat(),
                },
            )
            db.commit()
            ingested += 1

            if not transaction_id:
                orphaned += 1

            item.update(
                {
                    "status": "ingested",
                    "transaction_id": transaction_id or None,
                    "archive_path": archive_path,
                    "file_hash": file_hash,
                }
            )
        except Exception as exc:
            errors += 1
            item["reason"] = str(exc)

        manifest.append(item)

    return IngestResponse(
        total_files_found=total_found,
        ingested=ingested,
        linked=linked,
        orphaned=orphaned,
        errors=errors,
        bytes_copied=bytes_copied,
        manifest=[IngestResultItem(**m) for m in manifest],
    )


# ── Verify ───────────────────────────────────────────
@router.post("/verify", response_model=VerifyResult)
def verify_archive(req: VerifyRequest, db: Session = Depends(get_db)):
    q = "SELECT * FROM supporting_documents WHERE 1=1"
    params = {}
    if req.module_name:
        q += " AND module_name = :mn"
        params["mn"] = req.module_name

    rows = db.execute(text(q), params).fetchall()
    docs = [dict(r._mapping) for r in rows]
    total_checked = len(docs)
    verified = 0
    modified = 0
    missing = 0
    errors = 0

    for doc in docs:
        try:
            ap = doc.get("archive_path")
            if not ap or not Path(ap).exists():
                missing += 1
                db.execute(
                    text(
                        "UPDATE supporting_documents SET status = 'missing' WHERE id = :id"
                    ),
                    {"id": doc["id"]},
                )
                continue
            current_hash = _compute_file_hash(Path(ap))
            if current_hash == doc.get("file_hash_sha256"):
                verified += 1
                db.execute(
                    text(
                        "UPDATE supporting_documents SET status = 'verified', verified_at = :now WHERE id = :id"
                    ),
                    {"id": doc["id"], "now": datetime.now().isoformat()},
                )
            else:
                modified += 1
                db.execute(
                    text(
                        "UPDATE supporting_documents SET status = 'modified' WHERE id = :id"
                    ),
                    {"id": doc["id"]},
                )
        except Exception:
            errors += 1
    db.commit()
    return VerifyResult(
        total_checked=total_checked,
        verified=verified,
        modified=modified,
        missing=missing,
        errors=errors,
    )


# ── Query ────────────────────────────────────────────
@router.get("/", response_model=DocumentListResponse)
def list_documents(
    module: Optional[str] = Query(None),
    function: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    transaction_table: Optional[str] = Query(None),
    transaction_id: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = "SELECT * FROM supporting_documents WHERE 1=1"
    params = {}
    if module:
        q += " AND module_name = :module"
        params["module"] = module
    if function:
        q += " AND function_name = :function"
        params["function"] = function
    if status:
        q += " AND status = :status"
        params["status"] = status
    if transaction_table:
        q += " AND transaction_table = :transaction_table"
        params["transaction_table"] = transaction_table
    if transaction_id:
        q += " AND transaction_id = :transaction_id"
        params["transaction_id"] = transaction_id
    count_q = "SELECT COUNT(*) FROM supporting_documents WHERE 1=1"
    if module:
        count_q += " AND module_name = :module"
    if function:
        count_q += " AND function_name = :function"
    if status:
        count_q += " AND status = :status"
    if transaction_table:
        count_q += " AND transaction_table = :transaction_table"
    if transaction_id:
        count_q += " AND transaction_id = :transaction_id"
    total = db.execute(text(count_q), params).scalar() or 0
    rows = db.execute(
        text(q + " ORDER BY ingested_at DESC LIMIT :limit OFFSET :skip"),
        {**params, "limit": limit, "skip": skip},
    ).fetchall()
    items = [dict(r._mapping) for r in rows]
    return DocumentListResponse(total=total, items=items)


@router.get("/modules", response_model=DocumentModuleList)
def list_modules(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT * FROM document_modules")).fetchall()
    modules = [dict(r._mapping) for r in rows]
    return DocumentModuleList(modules=modules)


SEED_DATA = [
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
    ("Sales", "POs", "purchase_orders", "Client purchase orders", "PO_{id}_client.pdf"),
    ("Sales", "Contracts", "events", "Client contracts", "EVT_{id}_contract.pdf"),
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
    ("Purchase", "GRN", "purchase_orders", "Goods receipt notes", "GRN_{id}_*.pdf"),
    ("Events", "Work_Orders", "work_orders", "WO documentation", "WO_{id}_*.pdf"),
    ("Events", "Staff_Assignments", "staff_assignments", "Staff docs", "SA_{id}_*.pdf"),
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
    ("E_Invoice", "QR_Codes", "sales_invoices", "QR code images", "INV_{id}_qr.png"),
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
    ("Costing", "Budget", "budget_lines", "Budget approvals", "BUD_{id}_*.xlsx"),
    ("Costing", "SCM", "scm_staging", "SCM analysis docs", "SCM_{id}_*.xlsx"),
    ("OR", "Analysis", "or_analyses", "OR engine outputs", "OR_{engine}_{id}.json"),
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


@router.post("/modules/seed")
def seed_modules(db: Session = Depends(get_db)):
    inserted = 0
    for row in SEED_DATA:
        exists = db.execute(
            text(
                "SELECT 1 FROM document_modules WHERE module_name = :mn AND function_name = :fn"
            ),
            {"mn": row[0], "fn": row[1]},
        ).scalar()
        if not exists:
            db.execute(
                text(
                    "INSERT INTO document_modules (module_name, function_name, transaction_table, description, filename_pattern) VALUES (:mn, :fn, :tt, :desc, :fp)"
                ),
                {
                    "mn": row[0],
                    "fn": row[1],
                    "tt": row[2],
                    "desc": row[3],
                    "fp": row[4],
                },
            )
            inserted += 1
    db.commit()
    return {"seeded": inserted, "message": f"Inserted {inserted} module configurations"}


@router.get("/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT * FROM supporting_documents WHERE id = :id"), {"id": doc_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return dict(row._mapping)


@router.delete("/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    db.execute(
        text("UPDATE supporting_documents SET status = 'missing' WHERE id = :id"),
        {"id": doc_id},
    )
    db.commit()
    return {"message": "Document soft-deleted", "id": doc_id}
