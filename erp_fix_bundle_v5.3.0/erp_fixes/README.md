# ERP Fix Bundle — v5.3.0

Generated: 2026-06-11
Target system: ERP v5.3.0 (port 9001)

---

## Files in this bundle

| File | Purpose | Effort |
|------|---------|--------|
| `fix_client_endpoint.py` | Fix A — diagnose & patch /api/v1/env/clients → 0 | 5 min |
| `update_module_status.py` | Fix B — rebuild module status map from live counts | 5 min |
| `anomaly_scan.py` | Fix C — full diagnostic scan across all endpoints | 10 min |
| `phase5_event_operations.py` | Phase 5 — full Event Operations module | see below |

---

## Quick Start — Run Fixes

```bash
# 1. Full diagnostic first (read-only, safe to run anytime)
python anomaly_scan.py --base-url http://localhost:9001 --json

# 2. Fix the client endpoint (dry-run first, then apply)
python fix_client_endpoint.py
python fix_client_endpoint.py --apply

# 3. Rebuild module status map
python update_module_status.py --base-url http://localhost:9001
python update_module_status.py --base-url http://localhost:9001 --apply
```

---

## Phase 5 — Event Operations Module

`phase5_event_operations.py` is a self-extracting monolith.
Run it once to split itself into the correct project structure:

```bash
# Run from your project root
python phase5_event_operations.py
```

This creates:
```
models/event_ops.py              ← SQLAlchemy ORM (5 tables)
schemas/event_ops.py             ← Pydantic v2 schemas
services/event_ops.py            ← Business logic + status machine
routers/event_ops_router.py      ← FastAPI router (15 endpoints)
migrations/add_event_ops.py      ← Table creation helper
_MAIN_SNIPPET.py                 ← Paste into main.py
```

Then:
```bash
python migrations/add_event_ops.py --create
# paste _MAIN_SNIPPET.py into main.py
# restart server
```

### New Endpoints (prefix: /api/v1/evops)

```
GET    /summary                   List all events (paginated, filterable)
GET    /stats                     KPI dashboard: status breakdown, budget utilisation
POST   /                          Create event
GET    /{id}                      Full event detail with tasks/milestones/resources/notes
GET    /pnr/{pnr_ref}             Lookup by PNR reference
PATCH  /{id}                      Update event fields
PATCH  /{id}/status               Status machine transition
DELETE /{id}                      Soft delete

POST   /{id}/tasks                Add task
PATCH  /tasks/{task_id}           Update/complete task
DELETE /tasks/{task_id}           Remove task

POST   /{id}/milestones           Add milestone
PATCH  /milestones/{id}/achieve   Mark milestone achieved

POST   /{id}/resources            Attach resource (auto-updates actual_cost)
POST   /{id}/notes                Add internal/external note
```

### Status Machine
```
DRAFT → PLANNED → CONFIRMED → IN_PROGRESS → COMPLETED
         ↓           ↓            ↓
       ON_HOLD    ON_HOLD      ON_HOLD
         ↓                       
       CANCELLED (from any state except COMPLETED)
```

---

## Verification Checklist (post-fix)

- [ ] `GET /api/v1/env/clients` → `{"total": 49, ...}`
- [ ] `GET /api/v1/grn/summary` → `{"total_receipts": 20, ...}`
- [ ] `python anomaly_scan.py` → 0 anomalies
- [ ] `GET /api/v1/evops/summary` → `{"total": 143, "active": 12, ...}`
- [ ] `GET /api/v1/evops/stats` → budget utilisation, task completion %

---

## Next Phases

| Phase | Module | Key Deliverable |
|-------|--------|-----------------|
| 6 | Approval Workflow | Multi-step approval engine with roles |
| 7 | BI Charts & Neural Predictions | Dashboard charts + ML forecasting |
| 8 | Import SAL/PUR/GL Excel | Bulk data import pipeline |
