# BIO-ERP Event Operations — Integration Guide
## Phases 3-5 Deployment

---

## 1. FILE PLACEMENT

Copy these files to your BIO-ERP project at `D:\ERP System\BIO_ERP\`:

| File | Destination | Purpose |
|------|-------------|---------|
| `auto_recognition.py` | `app/services/auto_recognition.py` | Smart form pre-population engine |
| `event_ops_router.py` | `app/routers/event_ops.py` (overwrite) | Execution queue + auto-recognize APIs |
| `ops_execution_form.html` | `app/templates/ops_execution_form.html` | Operations team frontend form |
| `event_checkpoint_model.py` | `app/models/event_checkpoint.py` | Checkpoint ORM model |
| `5c4f_event_ops_lifecycle.py` | `alembic/versions/5c4f_event_ops_lifecycle.py` | DB migration |

---

## 2. DATABASE MIGRATION

```bash
cd "D:\ERP System\BIO_ERP"
alembic upgrade 5c4f_event_ops_lifecycle
```

**What it adds:**
- 11 new columns to `events` table (lifecycle_status, ops_team_id, execution_date, etc.)
- New `event_checkpoints` table (stage-gate checklist)
- UOM fields to `sales_line_items` (uom, buffer_percent, vendor_id, status)
- Default event status enum values

---

## 3. WIRE ROUTER INTO MAIN APP

Edit `app/main.py` — ensure this line exists:

```python
from app.routers import event_ops

# ... in app creation ...
app.include_router(event_ops.router, prefix="/api/v1")
```

---

## 4. EVENT MODEL RELATIONSHIP

Edit `app/models/event.py` — add to `Event` class:

```python
from sqlalchemy.orm import relationship

checkpoints = relationship("EventCheckpoint", back_populates="event", cascade="all, delete-orphan")
```

---

## 5. ACCESS THE FORM

After server restart:

```
http://localhost:8000/event-ops/{event_id}/execute
```

Or via API:
```bash
curl http://localhost:8000/api/v1/event-ops/execution-queue
```

---

## 6. TEST SUITE

Add to `tests/test_event_ops.py`:

```python
def test_execution_queue(client, db):
    res = client.get("/api/v1/event-ops/execution-queue")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

def test_auto_recognize(client, db):
    res = client.get("/api/v1/event-ops/events/1/auto-recognize")
    assert res.status_code == 200
    data = res.json()
    assert "category_uom_map" in data
    assert "execution_checklist" in data

def test_checkpoint_update(client, db):
    res = client.post("/api/v1/event-ops/events/1/checkpoints/venue_contract",
        json={"completed": True, "notes": "Signed"})
    assert res.status_code == 200
```

---

## 7. SALES CATEGORY → UOM MAPPING

| Category | UOM | Buffer % | Auto-Vendor | Special Fields |
|----------|-----|----------|-------------|----------------|
| Air Tickets | Each | 0% | Airline | Passport required |
| Launch Meeting | Day | 10% | Venue | Setup hours |
| Catering | Pax | 10% | Caterer | Dietary requirements |
| Ground Transport | Trip | 15% | Transport fleet | Route plan |
| Hotel | Room-Night | 5% | Hotel chain | Passport required |
| AV/Production | Day | 0% | AV vendor | Setup hours |

---

## 8. CHECKLIST STAGES

| Stage | Key Checkpoints | Auto-Advance Trigger |
|-------|-----------------|----------------------|
| **Ops Assigned** | Team assigned, client confirm | Both done → Procurement |
| **Procurement** | Venue contract, caterer menu, AV quote | All done → Execution |
| **Execution** | Air tickets, transport, hotel, setup | All done → QA Check |
| **QA Check** | Ops manager walk-through, client sign-off | Both done → Completed |
| **Completed** | Final invoice, vendor payments, archive | All done → Closed |

---

## 9. NEXT STEPS AFTER DEPLOYMENT

| Priority | Action | Command |
|----------|--------|---------|
| 1 | Import real data from Docker | `python scripts/import_docker_to_pg.py` |
| 2 | Embed AI smart window | Add `<script src="/static/js/ai_widget.js">` to `base.html` |
| 3 | Add company logo | Update `templates/base.html` header/footer |
| 4 | Commit all changes | `git add . && git commit -m "v5.4.0 — Event ops lifecycle"` |
| 5 | Run full test suite | `pytest tests/ -v` |

---

## 10. TROUBLESHOOTING

| Issue | Cause | Fix |
|-------|-------|-----|
| `lifecycle_status` column missing | Migration not run | `alembic upgrade head` |
| 404 on `/event-ops/execute` | Router not mounted | Check `main.py` includes router |
| Auto-recognition returns empty | No client history | Import historical events first |
| Checklist not advancing | Pending required items | Complete all required checkpoints in stage |
| Form not auto-saving | `auto_save.js` missing | Ensure script is in `static/js/` |
