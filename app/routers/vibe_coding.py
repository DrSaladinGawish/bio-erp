"""
Vibe Coding Agent (VCA) Router
Part of ERP Builder Agent (EBA) v1.0
BIO-ERP — FastAPI Bridge for AI Code Generation
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.database import get_db
from app.models.vibe_coding import VibeCodingSession, VibeCodeTemplate

router = APIRouter(prefix="/vibe", tags=["Vibe Coding"])


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Natural language description of feature/bug/fix")
    language: str = Field(default="en", description="User language: ar | en")
    target_module: str = Field(default="general", description="Target organ: scm | or | far | bank | ih | general")
    auto_test: bool = Field(default=True, description="Auto-generate and run tests")
    auto_commit: bool = Field(default=False, description="Auto-commit to Git (requires approval if False)")
    context_files: Optional[List[str]] = Field(default=None, description="Existing files to use as context")


class GenerateResponse(BaseModel):
    session_id: str
    status: str
    message: str
    estimated_time: str
    message_ar: Optional[str] = None


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    progress_percent: int
    prompt: str
    language: str
    target_module: str
    generated_files: List[Dict[str, Any]]
    test_results: Optional[Dict[str, Any]]
    lint_results: Optional[List[Dict[str, Any]]]
    git_branch: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    retry_count: int


class ApprovalRequest(BaseModel):
    session_id: str
    action: str = Field(..., pattern="^(merge|reject|regenerate)$")
    notes: Optional[str] = None


class ApprovalResponse(BaseModel):
    session_id: str
    action: str
    status: str
    message: str
    message_ar: Optional[str] = None


class RefactorRequest(BaseModel):
    target_file: str = Field(..., description="Path to file to refactor")
    instructions: str = Field(..., description="Refactoring instructions")
    language: str = Field(default="en", description="ar | en")


class FixRequest(BaseModel):
    error_log: str = Field(..., description="Error log or traceback")
    target_file: Optional[str] = Field(default=None, description="File that caused error")
    language: str = Field(default="en", description="ar | en")


class SessionListResponse(BaseModel):
    sessions: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int



def generate_session_id() -> str:
    return f"vca-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{str(datetime.utcnow().microsecond)[:3]}"


def get_bilingual_message(en_msg: str, ar_msg: str, lang: str) -> tuple:
    if lang == "ar":
        return ar_msg, en_msg
    return en_msg, ar_msg



OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5-coder:7b"

OLLAMA_SYSTEM_PROMPT = """You are an expert Python code generator integrated into BIO-ERP.
Your task is to generate clean, production-ready Python code based on the user's request.
Rules:
1. Return ONLY valid Python code — no explanations, no markdown formatting, no backticks.
2. Use modern Python 3.11+ features (type hints, async/await, dataclasses).
3. Follow FastAPI/SQLAlchemy patterns used in BIO-ERP (async sessions, Pydantic v2).
4. Include proper error handling and input validation.
5. If the request is unclear, generate a reasonable default implementation.
6. Maximum 200 lines per response."""


async def process_vibe_session(session_id: str, prompt: str, target_module: str):
    import datetime as dt
    import httpx
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    import os
    import py_compile
    import tempfile

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(VibeCodingSession).where(VibeCodingSession.session_id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            return
        session.status = "generating"
        await db.commit()

        files = []
        try:
            ollama_payload = {
                "model": OLLAMA_MODEL,
                "system": OLLAMA_SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "max_tokens": 4096}
            }
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(OLLAMA_URL, json=ollama_payload)
                resp.raise_for_status()
                data = resp.json()
                code = data.get("response", "").strip()

            output_dir = os.path.join("app", "generated", target_module)
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, f"{session_id}.py")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            validation = {"valid": True, "errors": []}
            try:
                with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
                    tmp.write(code.encode("utf-8"))
                    tmp_path = tmp.name
                py_compile.compile(tmp_path, doraise=True)
                os.unlink(tmp_path)
            except py_compile.PyCompileError as e:
                validation = {"valid": False, "errors": [str(e)]}

            files.append({
                "path": file_path,
                "content": code[:2000],
                "type": "generated",
                "validation": validation,
                "model": OLLAMA_MODEL
            })

            session.generated_files = files
            session.status = "completed"
            session.completed_at = dt.datetime.utcnow()

        except httpx.RequestError as e:
            session.status = "failed"
            files.append({"error": f"Ollama unavailable: {e}"})
            session.generated_files = files
        except Exception as e:
            session.status = "failed"
            files.append({"error": str(e)})
            session.generated_files = files

        await db.commit()


@router.post("/generate", response_model=GenerateResponse)
async def vibe_generate(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    session_id = generate_session_id()

    session = VibeCodingSession(
        session_id=session_id,
        prompt=request.prompt,
        language=request.language,
        target_module=request.target_module,
        status="queued",
        generated_files=[],
        test_results=None,
        lint_results=None,
        retry_count=0
    )
    db.add(session)
    await db.commit()
    background_tasks.add_task(process_vibe_session, session_id, request.prompt, request.target_module)

    msg_en = f"Vibe coding session started. Session: {session_id}. Estimated: 30-60 seconds."
    msg_ar = f"بدأت جلسة البرمجة بالتصفح. الجلسة: {session_id}. الوقت المتوقع: 30-60 ثانية."

    primary, secondary = get_bilingual_message(msg_en, msg_ar, request.language)

    return GenerateResponse(
        session_id=session_id,
        status="queued",
        message=primary,
        estimated_time="30-60s",
        message_ar=secondary if request.language == "en" else None
    )


@router.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VibeCodingSession).where(VibeCodingSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    progress_map = {
        "queued": 5,
        "generating": 25,
        "validating": 50,
        "testing": 75,
        "awaiting_approval": 90,
        "merged": 100,
        "rejected": 100,
        "failed": 100
    }

    return SessionStatusResponse(
        session_id=session.session_id,
        status=session.status,
        progress_percent=progress_map.get(session.status, 0),
        prompt=session.prompt,
        language=session.language,
        target_module=session.target_module,
        generated_files=session.generated_files or [],
        test_results=session.test_results,
        lint_results=session.lint_results,
        git_branch=session.git_branch,
        created_at=session.created_at,
        completed_at=session.completed_at,
        retry_count=session.retry_count
    )


@router.post("/approve", response_model=ApprovalResponse)
async def approve_session(
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: str = "admin"
):
    result = await db.execute(
        select(VibeCodingSession).where(VibeCodingSession.session_id == request.session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")

    if session.status != "awaiting_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Session is not awaiting approval. Current status: {session.status}"
        )

    if request.action == "merge":
        session.status = "merged"
        session.approved_by = current_user
        session.approval_notes = request.notes or "Approved via API"
        msg_en = f"Session {request.session_id} approved and merged."
        msg_ar = f"تمت الموافقة على الجلسة {request.session_id} ودمجها."

    elif request.action == "reject":
        session.status = "rejected"
        session.approved_by = current_user
        session.approval_notes = request.notes or "Rejected via API"
        msg_en = f"Session {request.session_id} rejected."
        msg_ar = f"تم رفض الجلسة {request.session_id}."

    elif request.action == "regenerate":
        session.status = "queued"
        session.retry_count += 1
        session.approval_notes = request.notes or "Regeneration requested"
        msg_en = f"Session {request.session_id} queued for regeneration (attempt {session.retry_count})."
        msg_ar = f"تم وضع الجلسة {request.session_id} في قائمة الانتظار لإعادة التوليد (المحاولة {session.retry_count})."

    session.completed_at = datetime.utcnow()
    await db.commit()

    primary, secondary = get_bilingual_message(msg_en, msg_ar, session.language)

    return ApprovalResponse(
        session_id=request.session_id,
        action=request.action,
        status=session.status,
        message=primary,
        message_ar=secondary if session.language == "en" else None
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    status: Optional[str] = None,
    target_module: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(VibeCodingSession)

    if status:
        stmt = stmt.where(VibeCodingSession.status == status)
    if target_module:
        stmt = stmt.where(VibeCodingSession.target_module == target_module)

    from sqlalchemy import func as sqlfunc
    count_stmt = select(sqlfunc.count()).select_from(VibeCodingSession)
    if status:
        count_stmt = count_stmt.where(VibeCodingSession.status == status)
    if target_module:
        count_stmt = count_stmt.where(VibeCodingSession.target_module == target_module)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()
    stmt = stmt.order_by(VibeCodingSession.created_at.desc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    return SessionListResponse(
        sessions=[{
            "session_id": s.session_id,
            "status": s.status,
            "prompt": s.prompt[:100] + "..." if len(s.prompt) > 100 else s.prompt,
            "target_module": s.target_module,
            "created_at": s.created_at.isoformat(),
            "completed_at": s.completed_at.isoformat() if s.completed_at else None
        } for s in sessions],
        total=total,
        page=page,
        per_page=per_page
    )


@router.post("/refactor")
async def vibe_refactor(
    request: RefactorRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    session_id = generate_session_id()

    session = VibeCodingSession(
        session_id=session_id,
        prompt=f"REFACTOR: {request.target_file} — {request.instructions}",
        language=request.language,
        target_module="refactor",
        status="queued",
        generated_files=[{"target_file": request.target_file}],
        retry_count=0
    )
    db.add(session)
    await db.commit()
    background_tasks.add_task(process_vibe_session, session_id, session.prompt, session.target_module)

    msg_en = f"Refactor session started: {session_id}. Target: {request.target_file}"
    msg_ar = f"بدأت جلسة إعادة البناء: {session_id}. الهدف: {request.target_file}"
    primary, _ = get_bilingual_message(msg_en, msg_ar, request.language)

    return {
        "session_id": session_id,
        "status": "queued",
        "message": primary,
        "target_file": request.target_file
    }


@router.post("/fix")
async def vibe_fix(
    request: FixRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    session_id = generate_session_id()

    session = VibeCodingSession(
        session_id=session_id,
        prompt=f"FIX: {request.target_file or 'unknown'} — {request.error_log[:500]}",
        language=request.language,
        target_module="fix",
        status="queued",
        generated_files=[{"target_file": request.target_file}] if request.target_file else [],
        retry_count=0
    )
    db.add(session)
    await db.commit()
    background_tasks.add_task(process_vibe_session, session_id, session.prompt, session.target_module)

    msg_en = f"Auto-fix session started: {session_id}. Analyzing error log..."
    msg_ar = f"بدأت جلسة الإصلاح التلقائي: {session_id}. جارٍ تحليل سجل الأخطاء..."
    primary, _ = get_bilingual_message(msg_en, msg_ar, request.language)

    return {
        "session_id": session_id,
        "status": "queued",
        "message": primary,
        "error_preview": request.error_log[:200] + "..." if len(request.error_log) > 200 else request.error_log
    }


@router.post("/shutdown")
async def vibe_shutdown(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VibeCodingSession).where(
            VibeCodingSession.status.in_(["queued", "generating", "validating", "testing"])
        )
    )
    active = result.scalars().all()

    for session in active:
        session.status = "failed"
        session.completed_at = datetime.utcnow()

    await db.commit()

    return {
        "status": "shutdown",
        "sessions_stopped": len(active),
        "message": "All active vibe coding sessions have been stopped.",
        "message_ar": "تم إيقاف جميع جلسات البرمجة بالتصفح النشطة."
    }
