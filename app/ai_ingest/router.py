import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.auth import User

from app.ai_ingest.models import (
    AIDocumentIngestion, AIDocumentAnalysis, AISuggestedTransaction,
    AINeuralPatternLog, SuggestionStatus,
)
from app.ai_ingest.schemas import (
    DocumentUploadResponse, AnalysisResult, SuggestedTransactionOut,
    ReviewRequest, ProtocolResult, IngestionStatusOut, PatternLogOut,
)
from app.ai_ingest.upload import save_upload
from app.ai_ingest.archiver import archive_file
from app.ai_ingest.protocols.runner import ProtocolRunner
from app.ai_ingest.protocols.agent_protocol import (
    HallucinationError, IncitationError, OmissionError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai-ingest", tags=["AI Ingestion"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    filepath = save_upload(content, file.filename)

    doc = AIDocumentIngestion(
        filename=file.filename,
        original_filename=file.filename,
        file_path=filepath,
        file_size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by=user.id,
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        message="Document uploaded successfully",
    )


@router.post("/{doc_id}/analyze", response_model=ProtocolResult)
async def analyze_document_endpoint(
    doc_id: int,
    full_protocol: bool = Form(False),
    use_openai: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = await db.get(AIDocumentIngestion, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    runner = ProtocolRunner(db, performed_by=user.id)

    try:
        if full_protocol:
            result = await runner.run_full_pipeline(doc_id, use_openai=use_openai)
        else:
            result = await runner.run_agent_only(doc_id)
        await db.commit()
    except (HallucinationError, IncitationError, OmissionError) as e:
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Protocol violation",
                "protocol": "AI Agent",
                "violation_type": type(e).__name__,
                "message": str(e),
            },
        )
    except Exception:
        await db.rollback()
        raise

    success = result.get("status") in ("completed", "analyzed", "evaluated", "awaiting_user_decision")
    return ProtocolResult(
        success=success,
        gate=result.get("status", "unknown"),
        message=result.get("message", result.get("final_status", "completed")),
        data=result,
    )


@router.get("/{doc_id}/status", response_model=IngestionStatusOut)
async def get_ingestion_status(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    doc = await db.get(AIDocumentIngestion, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    analysis = None
    if doc.analysis_id:
        analysis = await db.get(AIDocumentAnalysis, doc.analysis_id)

    suggestion = None
    if analysis:
        result = await db.execute(
            select(AISuggestedTransaction).where(
                AISuggestedTransaction.analysis_id == analysis.id
            ).limit(1)
        )
        suggestion = result.scalar_one_or_none()

    return IngestionStatusOut(
        document_id=doc.id,
        filename=doc.filename,
        upload_status=doc.status,
        analysis_status=analysis.status.value if analysis and hasattr(analysis.status, 'value') else (analysis.status if analysis else None),
        suggestion_status=suggestion.status.value if suggestion and hasattr(suggestion.status, 'value') else (suggestion.status if suggestion else None),
        posted_jv_id=suggestion.posted_jv_id if suggestion else None,
    )


@router.get("/documents")
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AIDocumentIngestion).order_by(AIDocumentIngestion.id.desc()).offset(skip).limit(limit)
    )
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "status": d.status,
            "file_size_bytes": d.file_size_bytes,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.get("/suggestions", response_model=list[SuggestedTransactionOut])
async def list_suggestions(
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(AISuggestedTransaction).order_by(AISuggestedTransaction.id.desc())
    if status:
        query = query.where(AISuggestedTransaction.status == status)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/suggestions/{suggestion_id}", response_model=SuggestedTransactionOut)
async def get_suggestion(
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    suggestion = await db.get(AISuggestedTransaction, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return suggestion


@router.post("/suggestions/{suggestion_id}/review", response_model=ProtocolResult)
async def review_suggestion(
    suggestion_id: int,
    review: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    suggestion = await db.get(AISuggestedTransaction, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if review.action == "approve":
        suggestion.status = SuggestionStatus.approved
    elif review.action == "amend":
        suggestion.status = SuggestionStatus.amended
        if review.journal_lines:
            suggestion.journal_lines = [l.model_dump() for l in review.journal_lines]
            suggestion.total_debit = sum(l.debit for l in review.journal_lines)
            suggestion.total_credit = sum(l.credit for l in review.journal_lines)
    elif review.action == "reject":
        suggestion.status = SuggestionStatus.rejected

    suggestion.review_notes = review.notes
    suggestion.reviewed_by = user.id
    await db.commit()

    return ProtocolResult(
        success=True,
        gate="human_review",
        message=f"Suggestion {review.action}d",
        data={
            "suggestion_id": suggestion_id,
            "new_status": str(suggestion.status.value) if hasattr(suggestion.status, 'value') else str(suggestion.status),
        },
    )


@router.post("/suggestions/{suggestion_id}/post", response_model=ProtocolResult)
async def post_suggestion(
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    runner = ProtocolRunner(db, performed_by=user.id)
    result = await runner.execute_approved_suggestion(suggestion_id, user.id, amended=False)

    if not result["success"]:
        error_msg = result.get("errors", [result.get("error", "Surgery failed")])
        raise HTTPException(status_code=500, detail=error_msg)

    return ProtocolResult(
        success=True,
        gate="surgery",
        message=f"Posted via Surgery Protocol (Op: {result['gate_3_surgery']['operation_id']})",
        data=result,
    )


@router.post("/suggestions/{suggestion_id}/amend-and-post", response_model=ProtocolResult)
async def amend_and_post_suggestion(
    suggestion_id: int,
    review: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    runner = ProtocolRunner(db, performed_by=user.id)
    amendment_data = {}
    if review.journal_lines:
        amendment_data["amended_amount"] = sum(l.debit for l in review.journal_lines)
        amendment_data["amended_description"] = review.notes

    result = await runner.execute_approved_suggestion(
        suggestion_id, user.id, amended=True, amendment_data=amendment_data
    )

    if not result["success"]:
        error_msg = result.get("errors", [result.get("error", "Surgery failed")])
        raise HTTPException(status_code=500, detail=error_msg)

    return ProtocolResult(
        success=True,
        gate="surgery",
        message=f"Amended & posted via Surgery Protocol (Op: {result['gate_3_surgery']['operation_id']})",
        data=result,
    )


@router.get("/analysis/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    analysis = await db.get(AIDocumentAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.get("/patterns", response_model=list[PatternLogOut])
async def list_patterns(
    pattern_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(AINeuralPatternLog).order_by(AINeuralPatternLog.id.desc())
    if pattern_type:
        query = query.where(AINeuralPatternLog.pattern_type == pattern_type)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
