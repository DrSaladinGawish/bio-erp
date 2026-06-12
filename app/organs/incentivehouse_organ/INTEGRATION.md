# Co-Pilot Smart Module — Integration Guide
# IncentiveHouse ERP — Local AI Only

---

## 📁 FILE STRUCTURE

```
D:\ERP System\BIO_ERPpp\copilot├── __init__.py              # Package exports
├── engine.py                # Core AI (embeddings, OLMo, rules)
├── schemas.py               # Pydantic v2 models
├── event_assistant.py       # Module A: Smart Event Builder
├── po_assistant.py          # Module B: Intelligent PO Generator
├── recon_assistant.py       # Module C: Smart Reconciliation v2
├── financial_cockpit.py     # Module D: Live Financial Cockpit
├── notifications.py         # Contextual Alert Engine
├── router.py                # 19 FastAPI endpoints
└── PROOF_OF_CONCEPT.md     # ASCII mockups

D:\ERP System\BIO_ERP\static├── js\copilot-panel.js      # Floating smart panel
└── css\copilot.css          # Panel styles

D:\ERP System\BIO_ERP	emplates└── components\copilot_widget.html  # Jinja2 include
```

---

## 🔧 STEP-BY-STEP INTEGRATION

### Step 1: Copy Files

```bash
cd D:\ERP System\BIO_ERP

# Copy all copilot files
xcopy /E /I /Y "C:\path	o\downloaded\copilot" "app\copilot"

# Copy static assets
xcopy /E /I /Y "C:\path	o\downloaded\static" "static"
xcopy /E /I /Y "C:\path	o\downloaded	emplates" "templates"
```

### Step 2: Update requirements.txt

Add these lines to `requirements.txt`:

```
# Co-Pilot Local AI Stack (no cloud APIs)
sentence-transformers>=2.2.0      # Local embeddings (~80MB)
scikit-learn>=1.3.0                 # TF-IDF, similarity

# Optional (for enhanced capabilities)
torch>=2.0.0                        # For OLMo LLM
transformers>=4.30.0                # OLMo model loading
# spacy>=3.6.0                      # NLP entity extraction
```

Install:
```bash
pip install -r requirements.txt
```

### Step 3: Mount Router in main.py

Add to `app/main.py`:

```python
from app.copilot.router import router as copilot_router

# ... existing routers ...

# Mount Co-Pilot at /api/v1/copilot
app.include_router(copilot_router, prefix="/api/v1")

# OR if your app already has /api/v1 prefix:
# app.include_router(copilot_router)  # router has /copilot prefix built-in
```

### Step 4: Add Static Assets to Templates

In your base template (`templates/base.html` or similar):

```html
<!DOCTYPE html>
<html>
<head>
    <!-- ... existing head ... -->
    <link rel="stylesheet" href="/static/css/copilot.css">
</head>
<body data-form-type="{% block form_type %}dashboard{% endblock %}"
      data-entity-id="{% block entity_id %}{% endblock %}">

    <!-- ... page content ... -->

    <!-- Co-Pilot Panel -->
    <script src="/static/js/copilot-panel.js"></script>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

In each form template:

```html
{% extends "base.html" %}
{% block form_type %}event{% endblock %}
{% block entity_id %}{{ event.id }}{% endblock %}

<!-- Your form content -->
```

### Step 5: Restart Server

```bash
# Stop existing server
# Start with new code
python -m uvicorn app.main:app --reload --port 9001
```

---

## 🧪 CURL TESTS

### Health Check
```bash
curl http://localhost:9001/api/v1/copilot/health
```
Expected: `{"status":"healthy","service":"co-pilot","version":"1.0.0-local"}`

### Engine Status
```bash
curl http://localhost:9001/api/v1/copilot/status
```

### Smart Event Analysis
```bash
curl -X POST http://localhost:9001/api/v1/copilot/event/analyze   -H "Content-Type: application/json"   -d '{
    "client_id": 1,
    "client_name": "CISCO",
    "event_type": "Corporate Meeting",
    "proposed_budget": 750000,
    "start_date": "2026-06-15T00:00:00",
    "end_date": "2026-06-17T00:00:00",
    "expected_attendees": 100,
    "location": "Cairo"
  }'
```

### Generate POs
```bash
curl -X POST http://localhost:9001/api/v1/copilot/po/generate   -H "Content-Type: application/json"   -d '{
    "event_id": 1,
    "include_line_items": true,
    "budget_cap": 800000,
    "urgency": "normal"
  }'
```

### Batch Reconciliation
```bash
curl -X POST http://localhost:9001/api/v1/copilot/recon/batch   -H "Content-Type: application/json"   -d '{
    "transactions": [
      {
        "transaction_id": "TXN-001",
        "date": "2026-06-01T00:00:00",
        "narration": "CISCO payment INV-001",
        "credit": 45000,
        "bank_account": "Bnk_Cur",
        "reference": "INV-001"
      },
      {
        "transaction_id": "TXN-002",
        "date": "2026-06-02T00:00:00",
        "narration": "SALARY TRANSFER STAFF",
        "debit": 125000,
        "bank_account": "Bnk_Cur"
      }
    ],
    "auto_match_threshold": 0.85,
    "suggest_threshold": 0.60
  }'
```

### Financial Cockpit
```bash
curl http://localhost:9001/api/v1/copilot/financial/summary
```

### Contextual Panel
```bash
curl -X POST http://localhost:9001/api/v1/copilot/panel   -H "Content-Type: application/json"   -d '{
    "form_type": "event",
    "entity_id": 1,
    "user_role": "manager"
  }'
```

### Ask OLMo (Local LLM)
```bash
curl -X POST http://localhost:9001/api/v1/copilot/ask   -H "Content-Type: application/json"   -d '{
    "prompt": "What budget should I plan for a CISCO corporate event with 100 attendees?",
    "max_tokens": 256,
    "temperature": 0.7
  }'
```

---

## ⚙️ CONFIGURATION

### Environment Variables

```bash
# Optional: Enable OLMo LLM (heavy, loads on first use)
COPILOT_OLMO_SIZE=1b          # "1b" or "7b" or unset for rule-based only

# Optional: Disable embeddings (falls back to TF-IDF)
COPILOT_ENABLE_EMBEDDINGS=true

# Cache directory for models
COPILOT_CACHE_DIR=./.copilot_cache
```

### Customizing Business Rules

Edit `app/copilot/engine.py` in the `_load_default_rules()` method:

```python
self._rules = [
    {
        "name": "my_custom_rule",
        "condition": lambda ctx: ctx.get("my_field", 0) > threshold,
        "action": lambda ctx: Recommendation(
            id=self._gen_id(),
            type="action",
            title="My Alert",
            description="...",
            confidence=ConfidenceLevel.HIGH,
            confidence_score=0.95,
            reason="Custom business logic",
        ),
    },
]
```

---

## 📊 PERFORMANCE

| Operation | Without OLMo | With OLMo 1B | With OLMo 7B |
|-----------|-------------|--------------|--------------|
| Health check | <1ms | <1ms | <1ms |
| Event analysis | 10-50ms | 10-50ms | 10-50ms |
| PO generation | 20-100ms | 20-100ms | 20-100ms |
| Recon (100 txns) | 50-200ms | 50-200ms | 50-200ms |
| Financial cockpit | 30-100ms | 30-100ms | 30-100ms |
| OLMo generate (first) | N/A | 2-5 min load | 5-10 min load |
| OLMo generate (cached) | N/A | 500ms-2s | 1-5s |

**Memory:**
- Base engine: ~50MB
- + Embeddings: +80MB
- + spaCy: +50MB
- + OLMo 1B: +2GB
- + OLMo 7B: +14GB

---

## 🔒 SECURITY

- **No cloud APIs** — all processing is local
- **No data leaves your server**
- **OLMo models** are open-source and run entirely on your hardware
- **Embeddings** are computed locally
- **Pattern cache** is stored in local filesystem only

---

## 🐛 TROUBLESHOOTING

### ImportError: No module named 'sentence_transformers'
```bash
pip install sentence-transformers
```

### OLMo model fails to load
- Check available RAM (1B needs 2GB, 7B needs 14GB)
- First load downloads model — ensure internet connection
- Fallback: system works without OLMo (rule-based)

### Panel not showing
- Check browser console for JS errors
- Verify `/static/js/copilot-panel.js` is accessible
- Check `COPILOT_API_BASE` is set correctly

### Endpoints return 404
- Verify router is mounted in `main.py`
- Check URL path: `/api/v1/copilot/...`

---

## 📞 SUPPORT

All code is self-contained. No external dependencies beyond:
- FastAPI (already in your stack)
- Pydantic v2 (already in your stack)
- sentence-transformers (optional, pip install)
- scikit-learn (optional, pip install)
- torch + transformers (optional, for OLMo)

---

**Version:** 1.0.0-local
**Built:** 2026-06-11
**Modules:** A (Event) + B (PO) + C (Recon) + D (Financial) + Notifications
**Endpoints:** 19
**Lines of Code:** ~3,200
