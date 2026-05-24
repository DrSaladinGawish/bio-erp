import json
import logging
import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_logger = logging.getLogger("bioerp")


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        start = time.time()
        response: Response = await call_next(request)
        duration = time.time() - start

        response.headers["X-Correlation-ID"] = correlation_id

        extra = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        }
        _logger.info(json.dumps(extra))

        return response
