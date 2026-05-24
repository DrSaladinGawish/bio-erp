from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from prometheus_client.registry import CollectorRegistry
from fastapi import Response

REGISTRY = CollectorRegistry()

HTTP_REQUESTS = Counter(
    "bioerp_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

HTTP_LATENCY = Histogram(
    "bioerp_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

DB_CONNECTIONS = Gauge(
    "bioerp_db_connections_active",
    "Active database connections",
    registry=REGISTRY,
)

DB_QUERY_DURATION = Histogram(
    "bioerp_db_query_duration_seconds",
    "Database query latency",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25],
    registry=REGISTRY,
)

ETA_SUBMISSIONS = Counter(
    "bioerp_eta_submissions_total",
    "ETA submissions",
    ["status"],
    registry=REGISTRY,
)

ETA_QUEUE_SIZE = Gauge(
    "bioerp_eta_queue_size",
    "Current ETA queue size by status",
    ["status"],
    registry=REGISTRY,
)

ETA_LATENCY = Histogram(
    "bioerp_eta_api_duration_seconds",
    "ETA API call latency",
    ["endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    registry=REGISTRY,
)

ACTIVE_EVENTS = Gauge(
    "bioerp_active_events",
    "Currently active events",
    registry=REGISTRY,
)

TOTAL_REVENUE = Gauge(
    "bioerp_total_revenue_egp",
    "Total revenue in EGP",
    registry=REGISTRY,
)

PENDING_RFQS = Gauge(
    "bioerp_pending_rfqs",
    "Pending RFQ count",
    registry=REGISTRY,
)

WS_CLIENTS = Gauge(
    "bioerp_websocket_clients",
    "Connected WebSocket clients",
    registry=REGISTRY,
)

CELERY_QUEUE_DEPTH = Gauge(
    "bioerp_celery_queue_depth",
    "Celery task queue depth by queue",
    ["queue"],
    registry=REGISTRY,
)

APP_INFO = Info(
    "bioerp_app",
    "Application metadata",
    registry=REGISTRY,
)


def set_app_info(version: str, env: str):
    APP_INFO.info({"version": version, "environment": env})


def metrics_response():
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
