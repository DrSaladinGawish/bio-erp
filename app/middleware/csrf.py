from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

_logger = logging.getLogger("bioerp.csurf")

_CSRF_COOKIE = "csrf_token"
_CSRF_HEADER = "x-csrf-token"
_CSRF_FIELD = "_csrf"
_TOKEN_MAX_AGE = 3600  # 1 hour

_serializer: URLSafeTimedSerializer | None = None


def _get_serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        _serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
    return _serializer


def generate_csrf_token(session_id: str = "anonymous") -> str:
    """Generate a signed CSRF token with embedded expiration."""
    s = _get_serializer()
    return s.dumps(
        {
            "token": secrets.token_urlsafe(32),
            "sid": session_id,
            "expires": (datetime.now(timezone.utc) + timedelta(seconds=_TOKEN_MAX_AGE)).timestamp(),
        }
    )


def validate_csrf_token(token: str, max_age: int = _TOKEN_MAX_AGE) -> bool:
    """Validate a CSRF token's signature and expiration."""
    s = _get_serializer()
    try:
        data = s.loads(token, max_age=max_age)
        if not isinstance(data, dict) or "token" not in data or "expires" not in data:
            return False
        if datetime.now(timezone.utc).timestamp() > data["expires"]:
            return False
        return True
    except BadSignature:
        return False


def _is_api_path(path: str) -> bool:
    return path.startswith("/api/v1/") or path.startswith("/api/")


def _is_state_changing(method: str) -> bool:
    return method in ("POST", "PUT", "PATCH", "DELETE")


def _is_secure(request: Request) -> bool:
    """Determine if the request is HTTPS."""
    return request.url.scheme == "https"


# ---------------------------------------------------------------------------
# Route-level dependency for POST endpoints that need explicit CSRF validation
# ---------------------------------------------------------------------------


async def require_csrf(
    request: Request,
    csrf_token: Optional[str] = Cookie(None),
) -> None:
    """FastAPI dependency — validate CSRF token for cookie-authenticated routes.

    Usage:
        @router.post("/some-form-endpoint")
        async def handler(..., _csrf: None = Depends(require_csrf)):
            ...
    """
    # Bearer-authenticated requests are exempt (SPA + JWT pattern)
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return

    # Try header first
    header_token = request.headers.get(_CSRF_HEADER)
    if header_token and validate_csrf_token(header_token):
        return

    # Try form field
    if not header_token:
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            field_token = form.get(_CSRF_FIELD)
            if field_token and validate_csrf_token(str(field_token)):
                return

    # Cookie alone is not sufficient for double-submit pattern
    _logger.warning(
        "CSRF dependency failed: method=%s path=%s has_cookie=%s",
        request.method,
        request.url.path,
        bool(csrf_token),
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="CSRF token missing or invalid",
    )


# ---------------------------------------------------------------------------
# ASGI Middleware — sets cookie on GET, validates on state-changing methods
# ---------------------------------------------------------------------------


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip CSRF for API routes (JWT-authenticated) and read-only methods
        if _is_api_path(path) or not _is_state_changing(request.method):
            response = await call_next(request)
            # Set cookie on GET requests to non-API routes so forms can pick it up
            if request.method == "GET" and not _is_api_path(path):
                token = generate_csrf_token()
                response.set_cookie(
                    _CSRF_COOKIE,
                    token,
                    max_age=_TOKEN_MAX_AGE,
                    httponly=False,  # Must be readable by JS for X-CSRF-Token header
                    secure=_is_secure(request),
                    samesite="lax",
                    path="/",
                )
            return response

        # State-changing request to a non-API route — validate CSRF
        token = None

        # 1. Check header (preferred)
        token = request.headers.get(_CSRF_HEADER)

        # 2. Check form body
        if not token:
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                form = await request.form()
                token = form.get(_CSRF_FIELD)

        # 3. Check JSON body
        if not token:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body = await request.json()
                    if isinstance(body, dict):
                        token = body.get(_CSRF_FIELD)
                except Exception:
                    pass

        # 4. Check cookie (last resort — cookie alone is not sufficient for double-submit)
        if not token:
            token = request.cookies.get(_CSRF_COOKIE)

        if not token or not validate_csrf_token(str(token)):
            _logger.warning(
                "CSRF validation failed: method=%s path=%s has_token=%s",
                request.method,
                path,
                bool(token),
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid"},
            )

        response = await call_next(request)
        return response
