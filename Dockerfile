# =============================================================================
#  IncentiveHouse ERP — Production container
# =============================================================================
#  Multi-stage build:
#    * builder   — installs Python deps into a virtual env
#    * runtime   — slim base, copies venv, runs uvicorn
# =============================================================================

# ---------- Stage 1: builder ----------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build deps for any wheels that need compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

# Create virtual env and install
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r /app/requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HOST=0.0.0.0 \
    PORT=8001 \
    LOG_LEVEL=info \
    ALLOW_AUTO_CREATE=true

WORKDIR /app

# Install only runtime libs (libpq for psycopg2, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data /app/logs \
    && chown -R appuser:appuser /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appuser . /app/

USER appuser

EXPOSE 8001

# Healthcheck (uses /health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8001/health || exit 1

# Default: launch the IncentiveHouse FastAPI app on port 8001
CMD ["uvicorn", "app.organs.incentivehouse_organ.main:app", \
     "--host", "0.0.0.0", "--port", "8001", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
