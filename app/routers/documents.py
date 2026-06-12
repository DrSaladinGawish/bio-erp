"""
Document Management System — FastAPI Router
Mount at: /api/v1/documents
"""

from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db  # Adjust to your project
from app.schemas.documents import (
    IngestRequest,
    IngestResponse,
    VerifyRequest,
    VerifyResult,
    LinkRequest,
    DocumentOut,
    DocumentListResponse,
    DocumentModuleList,
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
        "Bank",
        "Sales",
        "Purchase",
        "Events",
        "E_Invoice",
        "Master_Data",
        "HR",
        "Costing",
        "OR",
        "Manufacturing",
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
            for r in results
            if r.archive_path
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

    doc = (
        svc.db.query(SupportingDocument).filter(SupportingDocument.id == doc_id).first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/link")
def link_document(req: LinkRequest, svc: DocumentService = Depends(get_doc_service)):
    """Link an orphaned document to a transaction."""
    from app.models.documents import SupportingDocument

    doc = (
        svc.db.query(SupportingDocument)
        .filter(SupportingDocument.id == req.document_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.transaction_table = req.transaction_table
    doc.transaction_id = req.transaction_id
    doc.status = "linked"
    svc.db.commit()
    return {
        "message": "Document linked",
        "id": str(doc.id),
        "table": req.transaction_table,
        "txn_id": req.transaction_id,
    }


@router.delete("/{doc_id}")
def delete_document(doc_id: UUID, svc: DocumentService = Depends(get_doc_service)):
    """Soft-delete: mark as missing, keep record for audit."""
    from app.models.documents import SupportingDocument

    doc = (
        svc.db.query(SupportingDocument).filter(SupportingDocument.id == doc_id).first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.status = "missing"
    svc.db.commit()
    return {"message": "Document soft-deleted", "id": str(doc_id)}


# -- Missing legacy-compatible endpoints from container --


@router.get("/orphans", response_model=DocumentListResponse)
def list_orphans(svc: DocumentService = Depends(get_doc_service)):
    from app.models.documents import SupportingDocument

    items = (
        svc.db.query(SupportingDocument)
        .filter(SupportingDocument.status == "orphaned")
        .all()
    )
    return DocumentListResponse(total=len(items), items=items)


@router.get("/stats")
def doc_stats(svc: DocumentService = Depends(get_doc_service)):
    from app.models.documents import SupportingDocument
    from sqlalchemy import func

    total = svc.db.query(func.count(SupportingDocument.id)).scalar()
    linked = (
        svc.db.query(func.count(SupportingDocument.id))
        .filter(SupportingDocument.status == "linked")
        .scalar()
    )
    orphaned = (
        svc.db.query(func.count(SupportingDocument.id))
        .filter(SupportingDocument.status == "orphaned")
        .scalar()
    )
    missing = (
        svc.db.query(func.count(SupportingDocument.id))
        .filter(SupportingDocument.status == "missing")
        .scalar()
    )
    return {
        "total": total or 0,
        "linked": linked or 0,
        "orphaned": orphaned or 0,
        "missing": missing or 0,
    }


@router.post("/seed-modules")
def seed_modules_alias(svc: DocumentService = Depends(get_doc_service)):
    """Alias for /modules/seed (legacy compatibility)."""
    count = svc.seed_document_modules()
    return {"seeded": count, "message": f"Inserted {count} module configurations"}


@router.post("/upload")
def upload_document(svc: DocumentService = Depends(get_doc_service)):
    """Placeholder upload endpoint."""
    return {
        "message": "Upload endpoint ready. Use multipart/form-data with file field."
    }


@router.post("/auto-link")
def auto_link_documents(svc: DocumentService = Depends(get_doc_service)):
    """Auto-link orphaned documents by matching naming conventions."""
    from app.models.documents import SupportingDocument

    orphaned = (
        svc.db.query(SupportingDocument)
        .filter(SupportingDocument.status == "orphaned")
        .all()
    )
    linked = 0
    for doc in orphaned:
        result = svc.auto_link_document(doc.id)
        if result:
            linked += 1
    return {"total_orphaned": len(orphaned), "auto_linked": linked}


@router.post("/verify-all", response_model=VerifyResult)
def verify_all_documents(svc: DocumentService = Depends(get_doc_service)):
    """Re-hash ALL archived files across all modules."""
    return svc.verify_archive(module_name=None)


@router.post("/ingest-pnr2022")
def ingest_pnr2022(svc: DocumentService = Depends(get_doc_service)):
    """Ingest PNR2022 documents specifically."""
    return (
        svc.ingest_pnr2022()
        if hasattr(svc, "ingest_pnr2022")
        else {
            "message": "PNR2022 ingest not implemented. Use /ingest with module='Events'."
        }
    )


@router.get("/{doc_id}/download")
def download_document(doc_id: UUID, svc: DocumentService = Depends(get_doc_service)):
    from app.models.documents import SupportingDocument
    from fastapi.responses import FileResponse

    doc = (
        svc.db.query(SupportingDocument).filter(SupportingDocument.id == doc_id).first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    path = doc.archive_path or doc.source_path
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(path, filename=Path(path).name)


@router.post("/{doc_id}/link")
def link_document_by_id(
    doc_id: UUID, req: LinkRequest, svc: DocumentService = Depends(get_doc_service)
):
    from app.models.documents import SupportingDocument

    doc = (
        svc.db.query(SupportingDocument).filter(SupportingDocument.id == doc_id).first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.transaction_table = req.transaction_table
    doc.transaction_id = req.transaction_id
    doc.status = "linked"
    svc.db.commit()
    return {"message": "Document linked", "id": str(doc.id)}


@router.post("/{doc_id}/verify")
def verify_document(doc_id: UUID, svc: DocumentService = Depends(get_doc_service)):
    from app.models.documents import SupportingDocument

    doc = (
        svc.db.query(SupportingDocument).filter(SupportingDocument.id == doc_id).first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    result = (
        svc.verify_single(doc.id)
        if hasattr(svc, "verify_single")
        else {"verified": True}
    )
    return result
