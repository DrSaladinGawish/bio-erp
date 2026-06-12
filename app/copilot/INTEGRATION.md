# Co-Pilot Smart Modules — Integration Guide

## Directory Structure

```
app/
  copilot/
    __init__.py            # Package init, exports all modules
    engine.py              # Core AI engine (OLMo + embeddings + rules)
    schemas.py             # Pydantic v2 request/response models
    event_assistant.py     # Smart Event Builder (Module A)
    po_assistant.py        # Intelligent PO Generator (Module B)
    recon_assistant.py     # Smart Reconciliation v2 (Module C)
    financial_cockpit.py   # Live Financial Cockpit (Module D)
    notifications.py       # Contextual alert system
    router.py              # 19 FastAPI endpoints
    PROOF_OF_CONCEPT.md    # ASCII mockups & visual design
  static/
    js/copilot-panel.js    # Floating smart panel (self-contained)
    css/copilot.css        # Panel styles + light/dark themes
  templates/
    components/copilot_widget.html  # Jinja2 include widget
```

## Integration Steps

### Step 1: Mount Router in main.py

```python
# In app/main.py
from app.copilot.router import router as copilot_router
app.include_router(copilot_router)  # mounts at /copilot
# Or with prefix:
# app.include_router(copilot_router, prefix="/api/v1")
```

### Step 2: Add static files to base template

```html
<!-- In your base.html <head> -->
<link rel="stylesheet" href="/static/css/copilot.css">

<!-- Before </body> -->
<script src="/static/js/copilot-panel.js"></script>
```

### Step 3: Add widget to any form

```html
<!-- Auto-inits based on data attributes -->
<div data-form-type="event" data-entity-id="{{ event.id }}">
    {% include 'components/copilot_widget.html' %}
</div>
```

### Step 4: Install dependencies (optional, for full AI)

```bash
pip install sentence-transformers scikit-learn
# pip install torch transformers  # for OLMo LLM support
```

The engine gracefully degrades to rule-based if no ML libs are installed.

## API Endpoints (19 total)

| Method | Endpoint | Module | Description |
|--------|----------|--------|-------------|
| GET | `/copilot/health` | Core | Health check |
| GET | `/copilot/status` | Core | Engine status |
| POST | `/copilot/event/analyze` | A | Full event analysis |
| POST | `/copilot/event/templates` | A | Event templates |
| POST | `/copilot/event/budget` | A | Budget recommendation |
| POST | `/copilot/event/vendors` | A | Vendor recommendations |
| POST | `/copilot/event/staff` | A | Staff recommendations |
| POST | `/copilot/po/generate` | B | Generate POs |
| POST | `/copilot/po/optimize` | B | Optimize supplier selection |
| POST | `/copilot/recon/batch` | C | Batch reconciliation |
| POST | `/copilot/recon/single` | C | Single reconcile |
| POST | `/copilot/recon/learn` | C | Learn from correction |
| GET | `/copilot/recon/patterns` | C | View learned patterns |
| GET | `/copilot/financial/events` | D | Event P&L |
| GET | `/copilot/financial/cashflow` | D | Cash flow projection |
| GET | `/copilot/financial/summary` | D | Company financial summary |
| POST | `/copilot/panel` | UI | Contextual panel data |
| POST | `/copilot/ask` | UI | Ask AI question |
| GET | `/copilot/engine-status` | Core | Detailed engine status |

## Module Overview

### Module A: Smart Event Builder
- Detects event type from name/description
- Suggests budget range based on type + guest count
- Recommends top vendors by category
- Recommends staff roles by type
- Flags risks (no client, low guest count, budget misalignment)

### Module B: Intelligent PO Generator
- Auto-generates PO lines from event
- Enforces budget guardrails (ok/warning/over_budget)
- Scores suppliers by performance + backlog
- Detects duplicate POs
- Optimizes supplier selection by category

### Module C: Smart Reconciliation v2
- Fuzzy matching by amount + narration + date
- Auto-categorizes transactions by narration keywords
- Learns from manual corrections (pattern memory)
- Returns matched/suspicious/unmatched triage
- Confidence scoring per match

### Module D: Financial Cockpit
- Real-time P&L with margin analysis
- Cash flow projection (8-week horizon)
- Budget variance tracking by line item
- Smart alerts (budget, PO, vendor, revenue)

## Local AI Capabilities

| Feature | With sentence-transformers | Rule-only |
|---------|---------------------------|-----------|
| Semantic similarity | ✅ 80MB model | TF-IDF fallback |
| Pattern matching | ✅ Embedding-based | Keyword-based |
| Categorization | ✅ Semantic + keyword | Keyword-only |
| Text generation | With OLMo optional | Template responses |
| Confidence | Embedding score | Keyword match % |

## Testing

```bash
# Test health
curl http://localhost:9003/copilot/health

# Test event analysis
curl -X POST http://localhost:9003/copilot/event/analyze \
  -H "Content-Type: application/json" \
  -d '{"event_name":"Annual Gala","event_type":"corporate","budget":250000,"guest_count":200}'

# Test panel
curl -X POST http://localhost:9003/copilot/panel \
  -H "Content-Type: application/json" \
  -d '{"form_type":"event"}'

# Test reconciliation
curl -X POST http://localhost:9003/copilot/recon/batch \
  -H "Content-Type: application/json" \
  -d '{"transactions":[{"id":"T1","amount":45000,"narration":"Catering deposit"}]}'
```
