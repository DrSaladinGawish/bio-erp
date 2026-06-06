from fastapi import APIRouter
from app.services.email_service import EmailService, SMTP_USER

router = APIRouter(prefix="/api/v1/intelligence", tags=["Intelligence"])


@router.post("/email/trigger")
async def trigger_email(data: dict):
    to = data.get("to", "")
    subject = data.get("subject", "")
    body = data.get("body", "")
    if not to or not subject:
        return {"status": "error", "message": "to and subject required"}
    return {
        "status": "queued",
        "to": to,
        "subject": subject,
        "smtp_configured": bool(SMTP_USER),
    }
