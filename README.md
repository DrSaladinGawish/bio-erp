# 🏢 IncentiveHouse ERP v2.2.2

**Enterprise Resource Planning System** for IncentiveHouse — Event Management, Sales, Purchasing, Financial, and Operations modules with integrated Bank Reconciliation, OR (Operations Research), and SCM (Supply Chain Management) sub-apps.

---

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Docker](#docker)
- [GitHub Actions CI/CD](#github-actions-cicd)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

| Module | Status | Description |
|--------|--------|-------------|
| **Dashboard** | ✅ Live | KPI cards, revenue charts, pipeline grid, activity log |
| **Event Management** | ✅ Live | CRUD, lifecycle stages, line items, staff assignments |
| **Sales** | ✅ Live | Invoices, quotes, categories, VAT 14% auto-calc |
| **Purchasing** | ✅ Live | POs, vendors, three-way match |
| **Financial** | ✅ Live | Bank reconciliation, journal entries, COA, reports |
| **Operations** | ✅ Live | Staff schedule, delivery tracking, calendar |
| **Bank Reconciliation** | ✅ Live | ERP Builder Protocol: Extract → Validate → Stage → Reconcile → Promote |
| **Reports** | ✅ Live | P&L, Balance Sheet, Cash Flow, AR Aging, Tax, Commission |
| **Settings** | ✅ Live | Company, users/roles, financial, sales, events, notifications, security, integrations, backup, audit |
| **Search** | ✅ Live | Global search across all modules with Ctrl+K shortcut |
| **OR Module** | ✅ Integrated | 12 OR engines, 19 API endpoints, planning & analysis |
| **SCM Module** | 🔄 Planned | Strategic cost management + sustainability costing |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Database** | PostgreSQL 15, SQLAlchemy 2.0, Alembic |
| **Frontend** | Jinja2, HTMX, vanilla JS, Chart.js |
| **Styling** | Custom CSS (dark theme, IncentiveHouse brand) |
| **Auth** | JWT (cookie-based), role-based access control |
| **Validation** | Pydantic v2 |
| **Testing** | pytest, pytest-asyncio, httpx |
| **Container** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/YOUR_USERNAME/incentivehouse-erp.git
cd incentivehouse-erp
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

### 2. Environment

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 3. Database

```bash
alembic upgrade head
```

### 4. Run

```bash
python -m app.main
# Or: uvicorn app.main:app --host 0.0.0.0 --port 9001 --reload
```

### 5. Access

- **App**: http://localhost:9001
- **API Docs**: http://localhost:9001/docs (debug mode only)
- **OR Module Docs**: http://localhost:9001/api/v1/or/docs

---

## 📁 Project Structure

```
incentivehouse-erp/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app factory
│   ├── config.py               # Settings & env vars
│   ├── database.py             # DB connection & session
│   ├── models.py               # SQLAlchemy ORM (27 tables)
│   ├── schemas.py              # Pydantic v2 models
│   ├── static/
│   │   └── css/
│   │       └── erp-theme.css   # 832-line dark theme
│   ├── templates/
│   │   ├── base.html             # Shared layout (sidebar + header)
│   │   ├── login.html            # JWT auth page
│   │   ├── dashboard.html        # KPI landing page
│   │   ├── events.html           # Event CRUD + lifecycle
│   │   ├── sales.html            # Invoices + quotes
│   │   ├── purchasing.html       # POs + vendors
│   │   ├── finance.html          # Bank recon + journal + COA
│   │   ├── operations.html       # Staff + delivery + calendar
│   │   ├── bank_recon.html       # Dedicated recon page
│   │   ├── reports.html          # Reports hub (26 reports)
│   │   ├── settings.html         # 10 settings tabs
│   │   └── search.html           # Global search
│   ├── routers/
│   │   ├── __init__.py
│   │   └── pages.py              # Jinja2 page router (14 routes)
│   ├── services/                 # Business logic layer
│   ├── or_module/                # OR-ERP sub-app (12 engines)
│   └── scm_module/               # SCM sub-app (planned)
├── tests/                        # pytest suite
├── alembic/                      # Database migrations
├── .github/
│   └── workflows/
│       └── ci.yml                # CI/CD pipeline
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md                     # This file
```

---

## 🔐 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `IncentiveHouse ERP` | Application name |
| `APP_VERSION` | `v2.2.2` | Version string |
| `DEBUG` | `false` | Debug mode (enables docs, reload) |
| `PORT` | `9001` | Server port |
| `HOST` | `0.0.0.0` | Bind host |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection |
| `SECRET_KEY` | *(required)* | JWT signing key (256-bit) |
| `ALLOWED_ORIGINS` | `*` | CORS origins (production) |
| `WORKERS` | `4` | Uvicorn workers |

---

## 📚 API Documentation

### Core Endpoints

```
GET  /health                    → System health
GET  /api/v1/health             → API health
GET  /api/v1/status             → Full system status
GET  /api/v1/dashboard/summary   → Dashboard KPIs
GET  /api/v1/events             → Event list
POST /api/v1/events             → Create event
GET  /api/v1/events/{id}        → Event detail
GET  /api/v1/finance/invoices   → Invoice list
GET  /api/v1/purchase-orders    → PO list
GET  /api/v1/bank-reconciliation → Recon data
GET  /api/v1/or/...             → OR Module endpoints (19)
```

### OR Module Endpoints

Mounted at `/api/v1/or/` — see Swagger UI at `/api/v1/or/docs`:

- Linear Programming, Transportation, Assignment, Inventory, PERT/CPM, Decision Analysis, Game Theory, Queueing, Simulation, Forecasting, Markov Chains, Network Flow

---

## 🐳 Docker

### Build & Run

```bash
docker build -t incentivehouse-erp .
docker run -p 9001:9001 --env-file .env incentivehouse-erp
```

### Docker Compose (Full Stack)

```bash
docker-compose up -d
```

Includes: app + PostgreSQL + Nginx reverse proxy

---

## 🔄 GitHub Actions CI/CD

The pipeline runs on every push/PR:

1. **Lint** — `ruff`, `black`, `isort`
2. **Test** — `pytest` against PostgreSQL service container
3. **Build** — Docker image → GHCR
4. **Deploy** — Production deployment (configure your SSH/ECS/K8s)

### Required Secrets

| Secret | Purpose |
|--------|---------|
| `GITHUB_TOKEN` | Auto-provided, for GHCR push |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m "feat: add amazing feature"`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Code Style

- **Python**: Black formatter, Ruff linter, isort imports
- **HTML/CSS**: Consistent indentation, BEM-like naming
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)

---

## 📄 License

Proprietary — IncentiveHouse LLC. All rights reserved.

---

## 👤 Contact

**Mr. Maged** — Founder & Lead Developer  
📧 maged@incentivehouse.com  
🌐 https://incentivehouse.com

---

<p align="center">
  <b>IncentiveHouse ERP v2.2.2</b><br>
  <i>Built with precision. Powered by data.</i>
</p>
