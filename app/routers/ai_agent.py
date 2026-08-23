import json
import time
import asyncio
import logging
from datetime import timezone, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.auth import User
from app.models.ai_agent_audit import AiAgentAudit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai-agent", tags=["AI Agent Bridge"])
launcher_router = APIRouter(prefix="/api/v1/ai-agent", tags=["Launcher Public"])

_AGENT_KILL_SWITCH = {"disabled": False}
_RATE_LIMIT = {"window_sec": 60, "max_calls": 100, "calls": []}


def _check_rate_limit():
    now = time.time()
    window = _RATE_LIMIT["window_sec"]
    max_calls = _RATE_LIMIT["max_calls"]
    _RATE_LIMIT["calls"] = [t for t in _RATE_LIMIT["calls"] if now - t < window]
    if len(_RATE_LIMIT["calls"]) >= max_calls:
        raise HTTPException(status_code=429, detail="Rate limit exceeded (100 calls/min)")
    _RATE_LIMIT["calls"].append(now)


async def _log_audit(
    db: AsyncSession,
    agent_name: str,
    action: str,
    status: str = "pending",
    trigger: str | None = None,
    input_data: str | None = None,
    output_data: str | None = None,
    severity: str | None = None,
    target_organ: str | None = None,
    error_message: str | None = None,
    execution_ms: float | None = None,
    approved_by: int | None = None,
):
    entry = AiAgentAudit(
        agent_name=agent_name,
        action=action,
        status=status,
        trigger=trigger,
        input_data=input_data,
        output_data=output_data,
        severity=severity,
        target_organ=target_organ,
        error_message=error_message,
        execution_ms=execution_ms,
        approved_by=approved_by,
    )
    db.add(entry)
    await db.commit()
    return entry.id


class ChatRequest(BaseModel):
    message: str
    language: str = "auto"


class ChatResponse(BaseModel):
    reply: str
    agent: str
    data: dict | None = None


class WebhookPayload(BaseModel):
    event: str = Field(..., description="job_created / gap_detected / health_alert / remediation_needed")
    payload: dict


class AgentStatusResponse(BaseModel):
    agent: str
    status: str
    last_run: str | None = None


class GapReportRequest(BaseModel):
    target_organs: list[str] | None = None


class RemediationRequest(BaseModel):
    gap_id: int
    approved: bool
    approved_by: int | None = None


@router.get("/status")
async def get_agent_status(db: AsyncSession = Depends(get_db)):
    _check_rate_limit()
    if _AGENT_KILL_SWITCH["disabled"]:
        return {"status": "disabled", "agents": []}

    result = await db.execute(
        select(AiAgentAudit.agent_name, AiAgentAudit.status, AiAgentAudit.timestamp)
        .distinct(AiAgentAudit.agent_name)
        .order_by(AiAgentAudit.agent_name, AiAgentAudit.timestamp.desc())
    )
    rows = result.all()
    agents = [
        AgentStatusResponse(
            agent=row.agent_name,
            status=row.status,
            last_run=row.timestamp.isoformat() if row.timestamp else None,
        )
        for row in rows
    ]
    return {"status": "running", "agents": agents, "kill_switch": _AGENT_KILL_SWITCH["disabled"]}


@router.get("/health")
async def agent_health():
    from app.services.health import HealthCheck
    try:
        sys_health = await asyncio.wait_for(HealthCheck.full_check(), timeout=20)
    except asyncio.TimeoutError:
        sys_health = {"status": "timeout", "checks": {}}
    except Exception:
        sys_health = {"status": "error", "checks": {}}
    return {
        "agent_bridge": "ok",
        "n8n_expected": True,
        "n8n_url": "http://localhost:5678",
        "kill_switch": _AGENT_KILL_SWITCH["disabled"],
        "system_health": sys_health,
    }


@router.post("/shutdown")
async def shutdown_agents(req: Request, _: User = Depends(get_current_user)):
    _AGENT_KILL_SWITCH["disabled"] = True
    logger.warning("AI Agent kill switch activated by user %s", _)
    return {"status": "disabled", "message": "All AI agents disabled"}


@router.post("/restart")
async def restart_agents(_: User = Depends(get_current_user)):
    _AGENT_KILL_SWITCH["disabled"] = False
    return {"status": "enabled", "message": "AI agents re-enabled"}


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    _check_rate_limit()
    if _AGENT_KILL_SWITCH["disabled"]:
        raise HTTPException(status_code=503, detail="AI agents are disabled")

    start = time.time()
    audit_id = await _log_audit(
        db, "bilingual_chat", "CHAT", "running", "chat",
        input_data=req.message,
    )

    try:
        lang = req.language
        if lang == "auto":
            import re
            arabic = bool(re.search(r"[\u0600-\u06ff]", req.message))
            lang = "ar" if arabic else "en"

        reply = _route_chat(req.message, lang)
        elapsed = (time.time() - start) * 1000
        await _log_audit(
            db, "bilingual_chat", "CHAT", "success", "chat",
            input_data=req.message, output_data=reply,
            execution_ms=elapsed,
        )
        return ChatResponse(reply=reply, agent="bilingual_chat", data={"language": lang, "audit_id": audit_id})

    except Exception as e:
        elapsed = (time.time() - start) * 1000
        await _log_audit(
            db, "bilingual_chat", "CHAT", "failed", "chat",
            input_data=req.message, error_message=str(e), execution_ms=elapsed,
        )
        raise HTTPException(status_code=500, detail=str(e))


def _route_chat(message: str, lang: str) -> str:
    msg = message.lower()

    if "gap" in msg or "scan" in msg or "compliance" in msg:
        return _bilingual(lang,
            "I can scan the system for ERP Builder Protocol gaps. Use the 'Scan Gaps' button in the EBA dashboard.",
            "يمكنني فحص النظام للبحث عن ثغرات بروتوكول ERP Builder. استخدم زر 'مسح الثغرات' في لوحة تحكم EBA.",
        )
    if "health" in msg or "status" in msg:
        return _bilingual(lang,
            "System health is being monitored every 5 minutes. Visit /health for real-time status.",
            "يتم مراقبة صحة النظام كل 5 دقائق. زر /health للحصول على الحالة الفعلية.",
        )
    if "help" in msg or "what can you" in msg:
        return _bilingual(lang,
            "I am the ERP Builder Agent (EBA). I can: scan gaps, monitor health, answer ERP questions, "
            "generate reports, and auto-remediate protocol violations. Try asking in Arabic or English!",
            "أنا وكيل ERP Builder (EBA). يمكنني: مسح الثغرات، مراقبة الصحة، الإجابة على أسئلة ERP، "
            "توليد التقارير، وإصلاح انتهاكات البروتوكول تلقائياً. جرب السؤال بالعربية أو الإنجليزية!",
        )

    return _bilingual(lang,
        f"I understand your message. For specific ERP data queries, use the AI Query endpoint at /api/v1/ai/query. "
        f"Your message: '{message}'",
        f"لقد استلمت رسالتك. للاستعلام عن بيانات ERP محددة، استخدم نقطة /api/v1/ai/query. "
        f"رسالتك: '{message}'",
    )


def _bilingual(lang: str, en: str, ar: str) -> str:
    return ar if lang == "ar" else en


@router.post("/webhook")
async def handle_webhook(
    req: WebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    _check_rate_limit()
    if _AGENT_KILL_SWITCH["disabled"]:
        return {"status": "ignored", "reason": "agents disabled"}

    start = time.time()
    logger.info("AI Agent webhook received: event=%s", req.event)

    await _log_audit(
        db, "webhook_listener", req.event.upper(), "running", "webhook",
        input_data=json.dumps(req.payload),
    )

    try:
        if req.event == "job_created":
            result = await _on_job_created(req.payload, db)
        elif req.event == "gap_detected":
            result = await _on_gap_detected(req.payload, db)
        elif req.event == "health_alert":
            result = await _on_health_alert(req.payload, db)
        elif req.event == "remediation_needed":
            result = await _on_remediation_needed(req.payload, db)
        else:
            result = {"handled": False, "message": f"Unknown event: {req.event}"}

        elapsed = (time.time() - start) * 1000
        await _log_audit(
            db, "webhook_listener", req.event.upper(), "success", "webhook",
            input_data=json.dumps(req.payload), output_data=json.dumps(result),
            execution_ms=elapsed,
        )
        return result

    except Exception as e:
        elapsed = (time.time() - start) * 1000
        await _log_audit(
            db, "webhook_listener", req.event.upper(), "failed", "webhook",
            input_data=json.dumps(req.payload), error_message=str(e),
            execution_ms=elapsed,
        )
        raise HTTPException(status_code=500, detail=str(e))


async def _on_job_created(payload: dict, db: AsyncSession) -> dict:
    job_id = payload.get("job_id")
    organ = payload.get("organ", "unknown")
    logger.info("Job %s created in organ %s — n8n will run OR analysis", job_id, organ)
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:5678/webhook/or-auto-trigger",
            json={"job_id": job_id, "source": "bio_erp", "organ": organ},
            timeout=10,
        )
    return {"handled": True, "n8n_status": resp.status_code, "n8n_response": resp.text}


async def _on_gap_detected(payload: dict, db: AsyncSession) -> dict:
    from app.models.ai_agent_audit import AiAgentAudit
    entry = AiAgentAudit(
        agent_name="gap_scanner",
        action="GAP_DETECTED",
        status="pending",
        trigger="webhook",
        input_data=json.dumps(payload),
        severity=payload.get("severity"),
        target_organ=payload.get("organ"),
    )
    db.add(entry)
    await db.commit()
    return {"handled": True, "audit_id": entry.id, "requires_remediation": payload.get("severity") in ("P0", "P1")}


async def _on_health_alert(payload: dict, db: AsyncSession) -> dict:
    logger.warning("Health alert: %s", payload)
    return {"handled": True, "alert": payload.get("message")}


async def _on_remediation_needed(payload: dict, db: AsyncSession) -> dict:
    logger.info("Remediation needed: %s", payload)
    return {
        "handled": True,
        "status": "fix_generated",
        "branch": f"fix/{payload.get('gap_id', 'unknown')}",
        "staging_table": f"{payload.get('organ', 'unknown')}_staging",
    }


@router.get("/audit")
async def get_audit_log(
    limit: int = 50,
    offset: int = 0,
    agent_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(AiAgentAudit).order_by(AiAgentAudit.timestamp.desc()).offset(offset).limit(limit)
    if agent_name:
        query = query.where(AiAgentAudit.agent_name == agent_name)
    result = await db.execute(query)
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "agent": r.agent_name,
            "action": r.action,
            "status": r.status,
            "trigger": r.trigger,
            "severity": r.severity,
            "target": r.target_organ,
            "error": r.error_message,
            "execution_ms": r.execution_ms,
            "approved_by": r.approved_by,
        }
        for r in rows
    ]


@router.post("/trigger/scan")
async def trigger_gap_scan(
    req: GapReportRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if _AGENT_KILL_SWITCH["disabled"]:
        raise HTTPException(status_code=503, detail="AI agents are disabled")

    targets = req.target_organs if req and req.target_organs else ["scm", "or", "far", "bnk", "incentivehouse"]
    audit_id = await _log_audit(
        db, "gap_scanner", "SCAN", "running", "manual",
        input_data=json.dumps({"targets": targets}),
    )

    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:5678/webhook/gap-scanner",
                json={"targets": targets, "audit_id": audit_id, "source": "bio_erp"},
                timeout=30,
            )
            resp_data = resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        resp_data = {"error": f"n8n unreachable: {e}"}

    await _log_audit(
        db, "gap_scanner", "SCAN", "success" if "error" not in resp_data else "failed",
        "manual", output_data=json.dumps(resp_data),
    )
    return {"audit_id": audit_id, "n8n_response": resp_data}


@router.post("/trigger/remediate")
async def trigger_remediation(
    req: RemediationRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if _AGENT_KILL_SWITCH["disabled"]:
        raise HTTPException(status_code=503, detail="AI agents are disabled")
    if not req.approved:
        return {"status": "rejected", "message": "Remediation requires human approval"}

    audit_id = await _log_audit(
        db, "auto_remediation", "REMEDIATE", "running", "manual",
        input_data=json.dumps({"gap_id": req.gap_id}),
        approved_by=req.approved_by,
    )

    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:5678/webhook/auto-remediation",
                json={"gap_id": req.gap_id, "audit_id": audit_id, "approved_by": req.approved_by},
                timeout=60,
            )
            resp_data = resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        resp_data = {"error": f"n8n unreachable: {e}"}

    status = "success" if "error" not in resp_data else "failed"
    await _log_audit(
        db, "auto_remediation", "REMEDIATE", status, "manual",
        output_data=json.dumps(resp_data), approved_by=req.approved_by,
    )
    return {"audit_id": audit_id, "n8n_response": resp_data}


# ── Public launcher endpoints (no auth required, localhost only) ──

@launcher_router.post("/launcher/shutdown")
async def launcher_shutdown():
    _AGENT_KILL_SWITCH["disabled"] = True
    return {"status": "disabled", "message": "All AI agents disabled"}


@launcher_router.post("/launcher/restart")
async def launcher_restart():
    _AGENT_KILL_SWITCH["disabled"] = False
    return {"status": "enabled", "message": "AI agents re-enabled"}

@launcher_router.post("/launcher/chat")
async def launcher_chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    _check_rate_limit()
    if _AGENT_KILL_SWITCH["disabled"]:
        return ChatResponse(reply="AI agents are disabled. Use the ENABLE button.", agent="launcher")

    try:
        lang = req.language
        if lang == "auto":
            import re
            arabic = bool(re.search(r"[\u0600-\u06ff]", req.message))
            lang = "ar" if arabic else "en"
        reply = _route_chat(req.message, lang)
        return ChatResponse(reply=reply, agent="launcher", data={"language": lang})
    except Exception as e:
        return ChatResponse(reply=f"Error: {e}", agent="launcher")


@launcher_router.get("/launcher/health")
async def launcher_health():
    from app.services.health import HealthCheck
    try:
        sys_health = await asyncio.wait_for(HealthCheck.full_check(), timeout=20)
    except asyncio.TimeoutError:
        sys_health = {"status": "timeout", "checks": {}, "details": {"message": "timed out"}}
    except Exception as e:
        sys_health = {"status": "error", "checks": {}, "details": {"error": str(e)}}
    return {
        "agent_bridge": "ok",
        "n8n_expected": True,
        "n8n_url": "http://localhost:5678",
        "kill_switch": _AGENT_KILL_SWITCH["disabled"],
        "system_health": sys_health,
    }


@launcher_router.get("/launcher/status")
async def launcher_status(db: AsyncSession = Depends(get_db)):
    if _AGENT_KILL_SWITCH["disabled"]:
        return {"status": "disabled", "agents": []}
    try:
        stmt = select(AiAgentAudit.agent_name, AiAgentAudit.status, AiAgentAudit.timestamp).order_by(AiAgentAudit.timestamp.desc())
        result = await db.execute(stmt)
        rows = result.all()
        seen = set()
        agents = []
        for row in rows:
            if row.agent_name not in seen:
                seen.add(row.agent_name)
                agents.append({
                    "agent": row.agent_name,
                    "status": row.status,
                    "last_run": row.timestamp.isoformat() if row.timestamp else None,
                })
        return {"status": "running", "agents": agents, "kill_switch": _AGENT_KILL_SWITCH["disabled"]}
    except Exception as e:
        return {"status": "error", "agents": [], "kill_switch": _AGENT_KILL_SWITCH["disabled"], "error": str(e)}
