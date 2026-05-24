from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.database import async_session_factory
from app.models.audit import AuditLog
from datetime import datetime, timezone

_FINANCIAL_PATHS = [
    "/api/v1/finance",
    "/api/v1/invoice",
    "/api/v1/jv",
    "/api/v1/payment",
    "/api/v1/receipt",
    "/api/v1/budget",
    "/api/v1/cost",
    "/api/v1/procurement",
    "/api/v1/grn",
    "/api/v1/po",
    "/api/v1/rfq",
]


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return response

        path = request.url.path
        if not any(path.startswith(p) for p in _FINANCIAL_PATHS):
            return response

        try:
            async with async_session_factory() as db:
                actor_id = None
                actor_name = None
                if hasattr(request.state, "user"):
                    actor_id = request.state.user.id
                    actor_name = request.state.user.username

                body = await request.body()
                body_text = (
                    body.decode("utf-8", errors="replace")[:2000] if body else None
                )

                entry = AuditLog(
                    timestamp=datetime.utcnow(),
                    actor_id=actor_id,
                    actor_name=actor_name,
                    action=request.method,
                    target_type=path,
                    new_value=body_text,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                db.add(entry)
                await db.commit()
        except Exception:
            pass

        return response
