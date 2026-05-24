# BIO_ERP v5 — Production Deployment Guide

## Quick Start (Docker Compose)

```bash
# 1. Clone and enter directory
git clone https://github.com/DrSaladinGawish/bio-erp.git
cd bio-erp

# 2. Configure secrets
cp .env.example .env
# Edit .env — set SECRET_KEY to a long random string

# 3. Launch
docker compose up -d

# 4. Verify
curl http://localhost:8000/health
```

## Manual Deployment

### Requirements
- Python 3.11+
- PostgreSQL 15
- pip/poetry

### Steps
```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# or: source .venv/bin/activate  # Linux/macOS

# 2. Install dependencies
pip install -e .

# 3. Configure environment
set SECRET_KEY=your-secret-key-here
set DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bio_erp

# 4. Run with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Production Hardening Checklist
- [ ] **SECRET_KEY** — generate with `openssl rand -hex 32`
- [ ] **HTTPS** — terminate TLS at reverse proxy (nginx/Caddy)
- [ ] **Database** — use managed PostgreSQL (RDS, Cloud SQL) with SSL
- [ ] **Auth** — change default admin password on first login
- [ ] **Logging** — configure structured JSON logging to stdout
- [ ] **Monitoring** — health endpoint at `/health` for load balancer probes
- [ ] **Backups** — schedule `pg_dump` or use DB snapshot feature

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Root info |
| GET | `/health` | No | Health check |
| GET | `/docs` | No | Swagger UI |
| POST | `/api/v1/accounting/login` | No | Get JWT token |
| GET | `/api/v1/accounting/coa` | Yes | Chart of Accounts tree |
| GET | `/api/v1/accounting/ledger-entries` | Yes | Paginated ledger inquiry |
| POST | `/api/v1/accounting/ledger-entries` | Yes | Create entry |
| PUT | `/api/v1/accounting/ledger-entries/{id}` | Yes | Update entry |
| DELETE | `/api/v1/accounting/ledger-entries/{id}` | Yes | Soft-delete entry |
