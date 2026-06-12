"""
Document Management System — FastAPI Router
Mount at: /api/v1/documents
"""
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db  # Adjust to your project
from app.schemas.documents import (
    IngestRequest, IngestResponse,
    VerifyRequest, VerifyResult, LinkRequest,
    DocumentOut, DocumentListResponse,
    DocumentModuleList, DocumentModuleOut,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


def get_doc_service(db: Session = Depends(get_db)) -> DocumentService:
    return DocumentService(db)


# ── Ingest ────────────────────────────────────────────
@router.post("/ingest", response_model=IngestResponse)
def ingest_documents(
    req: IngestRequest,
    svc: DocumentService = Depends(get_doc_service),
):
    """Ingest documents from USB into archive."""
    svc.ensure_archive_dirs()

    all_results = []
    total_found = 0
    total_ingested = 0
    total_linked = 0
    total_orphaned = 0
    total_errors = 0
    total_bytes = 0

    modules = req.modules or [
        "Bank", "Sales", "Purchase", "Events", "E_Invoice",
        "Master_Data", "HR", "Costing", "OR", "Manufacturing"
    ]

    for module in modules:
        results = svc.ingest_module(
            usb_drive=req.usb_drive_letter,
            usb_base=req.usb_base_path,
            module_name=module,
            auto_link=req.auto_link,
            copy_to_archive=req.copy_to_archive,
            compute_hash=req.compute_hash,
        )
        all_results.extend(results)
        total_found += len(results)
        total_ingested += sum(1 for r in results if r.status in ("linked", "orphaned"))
        total_linked += sum(1 for r in results if r.status == "linked")
        total_orphaned += sum(1 for r in results if r.status == "orphaned")
        total_errors += sum(1 for r in results if r.status == "error")
        total_bytes += sum(
            r.archive_path and Path(r.archive_path).stat().st_size or 0
            for r in results if r.archive_path
        )

    return IngestResponse(
        total_files_found=total_found,
        ingested=total_ingested,
        linked=total_linked,
        orphaned=total_orphaned,
        errors=total_errors,
        bytes_copied=total_bytes,
        manifest=all_results,
    )


# ── Verify ────────────────────────────────────────────
@router.post("/verify", response_model=VerifyResult)
def verify_archive(
    req: VerifyRequest,
    svc: DocumentService = Depends(get_doc_service),
):
    """Re-hash all archived files and update status."""
    return svc.verify_archive(module_name=req.module_name)


# ── Query ─────────────────────────────────────────────
@router.get("/", response_model=DocumentListResponse)
def list_documents(
    module: Optional[str] = Query(None),
    function: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    transaction_table: Optional[str] = Query(None),
    transaction_id: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    svc: DocumentService = Depends(get_doc_service),
):
    """List documents with filters."""
    from app.models.documents import SupportingDocument
    q = svc.db.query(SupportingDocument)

    if module:
        q = q.filter(SupportingDocument.module_name == module)
    if function:
        q = q.filter(SupportingDocument.function_name == function)
    if status:
        q = q.filter(SupportingDocument.status == status)
    if transaction_table:
        q = q.filter(SupportingDocument.transaction_table == transaction_table)
    if transaction_id:
        q = q.filter(SupportingDocument.transaction_id == transaction_id)

    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return DocumentListResponse(total=total, items=items)


@router.get("/transaction/{table}/{txn_id}", response_model=DocumentListResponse)
def get_transaction_documents(
    table: str,
    txn_id: str,
    svc: DocumentService = Depends(get_doc_service),
):
    """Get all documents linked to a specific transaction."""
    items = svc.get_by_transaction(table, txn_id)
    return DocumentListResponse(total=len(items), items=items)


@router.get("/modules", response_model=DocumentModuleList)
def list_modules(svc: DocumentService = Depends(get_doc_service)):
    """List all document module configurations."""
    from app.models.documents import DocumentModule
    mods = svc.db.query(DocumentModule).all()
    return DocumentModuleList(modules=mods)


@router.post("/modules/seed")
def seed_modules(svc: DocumentService = Depends(get_doc_service)):
    """Seed document_modules lookup table. Idempotent."""
    count = svc.seed_document_modules()
    return {"seeded": count, "message": f"Inserted {count} module configurations"}


# ── Single Document Ops ───────────────────────────────
@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: UUID, svc: DocumentService = Depends(get_doc_service)):
    from app.models.documents import SupportingDocument
    doc = svc.db.query(SupportingDocument).filter(SupportingDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/link")
def link_document(req: LinkRequest, svc: DocumentService = Depends(get_doc_service)):
    """Link an orphaned document to a transaction."""
    from app.models.documents import SupportingDocument
    doc = svc.db.query(SupportingDocument).filter(SupportingDocument.id == req.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.transaction_table = req.transaction_table
    doc.transaction_id = req.transaction_id
    doc.status = "linked"
    svc.db.commit()
    return {"message": "Document linked", "id": str(doc.id), "table": req.transaction_table, "txn_id": req.transaction_id}


@router.delete("/{doc_id}")
def delete_document(doc_id: UUID, svc: DocumentService = Depends(get_doc_service)):
    """Soft-delete: mark as missing, keep record for audit."""
    from app.models.documents import SupportingDocument
    doc = svc.db.query(SupportingDocument).filter(SupportingDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.status = "missing"
    svc.db.commit()
    return {"message": "Document soft-deleted", "id": str(doc_id)}
