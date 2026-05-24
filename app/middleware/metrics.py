import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.services.metrics import HTTP_REQUESTS, HTTP_LATENCY


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        path = request.url.path
        method = request.method
        status = str(response.status_code)

        if path != "/api/v1/monitoring/metrics":
            HTTP_REQUESTS.labels(method=method, endpoint=path, status_code=status).inc()
            HTTP_LATENCY.labels(method=method, endpoint=path).observe(duration)

        return response
