# BIO-ERP

Enterprise Resource Planning system for construction & industrial businesses, built with FastAPI + PostgreSQL + Redis.

## Quick Start (Docker Dev)

```powershell
docker compose -f docker-compose.dev.yml up -d --build
docker exec bioerp_api pip install pytest pytest-asyncio httpx pytest-cov
docker exec bioerp_api alembic upgrade head
docker exec bioerp_api python -m pytest -q
```

Open http://localhost:8000

## Stack

| Layer     | Technology                     |
|-----------|--------------------------------|
| API       | Python 3.11 / FastAPI          |
| Database  | PostgreSQL 15                  |
| Cache     | Redis 7                        |
| Queue     | Celery + Redis                 |
| Frontend  | Jinja2 + HTMX                  |
| Auth      | JWT (bcrypt 4.0.1)             |

## Key Modules

- **Costing** — hierarchical cost estimation tree
- **Finance** — chart of accounts, GL posting, currency sync
- **GRDSLAB** — ACI 360R concrete slab on grade calculator
- **ETA** — Egyptian e-invoicing integration
- **Events** — event management with budget tracking
- **Strategic** — strategic cost modeling

## Environment

Copy `.env.example` to `.env` and fill secrets:

```
DATABASE_URL=postgresql+asyncpg://bioerp:password@localhost:5432/bio_erp
SECRET_KEY=<generate-64-char-random>
```

## Testing

```powershell
# Inside container (pytest not persisted in image)
pip install pytest pytest-asyncio httpx pytest-cov
python -m pytest --cov=app -q
```

## Project Layout

```
app/
├── main.py                 # FastAPI application entry point
├── config.py               # Pydantic settings (env vars)
├── database.py             # SQLAlchemy async engine + session
├── models/                 # SQLAlchemy ORM models
├── routers/                # API route handlers
├── services/               # Business logic
├── schemas/                # Pydantic request/response schemas
├── grdslab/                # GRDSLAB calculator (ACI 360R)
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS / JS assets
└── tasks/                  # Celery background tasks
```

## License

Proprietary — BIO-ERP
