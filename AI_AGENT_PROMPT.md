# INCENTIVE HOUSE OF EGYPT — ERP BUILDER PROTOCOL v3.0
## Complete AI Agent Prompt for End-to-End Product Build

ROLE: Senior ERP Builder Agent for Incentive House of Egypt
MISSION: Build complete AI-Native ERP system from current state to production-ready product
AUTHORITY: Full filesystem access to D:\
CONSTRAINTS: ERP Builder Protocol — backup before modify, test after every change

---

## SECTION 1: CURRENT STATE (Verified)

| System | Location | Status |
|--------|----------|--------|
| BIO-ERP (Doctor) | `D:\ERP System\BIO_ERP` | Active — 374 routes, 210 tests |
| IHE-ERP (SQL Server) | `D:\Temp\opencode\IHE_ERP_SQL` | Fresh — 18 tables, 7 views |
| Document System | Embedded in BIO-ERP | Active — 1,008 docs (980 PNR + 28 monthly) |
| OR-ERP Module | `/api/v1/or/` | Active — 12 engines, 19 endpoints |
| Gen_Led Parsed | `D:\Data_Sources\docs\gen_led_parsed\` | CSVs ready (Bnk: 2,502, SAL: 452, PUR: 1,388) |

---

## SECTION 2: BUILD PHASES

### PHASE 1: Neural Infrastructure (P0)

**1.1 Create Neural Tables**
- `migrations/neural_system.sql` — DDL for 5 tables
- `app/models/neural/neural_nodes.py` — 5 ORM models
- Tables: `neural_nodes`, `neural_predictions`, `neural_feature_store`, `neural_training_history`, `neural_memory`

**1.2 Create Pydantic Schemas**
- `app/schemas/neural/nodes.py` — NeuralNodeCreate, PredictionRequest, HumanFeedback, TrainingRequest

**1.3 Create Predictor Services**
- `app/services/neural/predictor.py` — CashFlowPredictor, ClientChurnPredictor, PnrOverrunPredictor, TransactionAnomalyDetector

**1.4 Create API Router**
- `app/routers/neural/ai_api.py` — 7 endpoints: create/list nodes, predict, train, feedback, dashboard, insights

**1.5 Mount Router & Test**
- Patch `app/main.py` — add import + include_router
- `pytest tests/test_neural/ -v` — 10+ tests pass

### PHASE 2: AI Smart UI (P1)

**2.1 AI Assistant Component**
- Floating orb (48px, bottom-right, pulsing)
- Expandable panel (360x480px, 4 tabs: Insights/Predict/Help/Voice)
- Context-aware (reads form fields, page, user role)

**2.2 Smart Presentation Engine**
- Auto-detect data type → best visualization
- Trend sparklines, anomaly alerts, period comparisons

**2.3 Header/Footer with Logo**
- Header: Logo `ihe_logo.png`, brand name, navigation
- Footer: Small logo, copyright, system status, version

### PHASE 3: Gen_Led Transformer (P1)

**3.1 GL Tables** — `gl_accounts`, `gl_entries`, `gl_balances`
**3.2 Transformer** — Map Dr/Cr pairs to GL entries
**3.3 Reconciliation** — Match entries to `bnk_transactions`, `sales_invoices`, `purchase_orders`

### PHASE 4: 2023 Year-End Ingest

**4.1** Scan 2023 folder (Bank Recon, Payable, Sales Module, Events, Reports)
**4.2** Ingest as supporting_documents with module mapping

### PHASE 5: IHE-ERP Bridge (P2)

**5.1** Nightly sync: BIO-ERP → IHE-ERP (clients, vendors, events, invoices, POs, predictions)
**5.2** Unified views in SQL Server

### PHASE 6: Orphan Resolution

**6.1** Analyze 153 orphaned files
**6.2** Bulk linker with relaxed patterns
**6.3** Manual review UI

### PHASE 7: Production Prep

**7.1** Docker Compose update (neural-worker, redis)
**7.2** .env.example (neural vars, IHE connection)
**7.3** Docs: AI_MODULE.md, UI_GUIDE.md, DEPLOY_AI.md, TROUBLESHOOTING.md
**7.4** Monitoring: daily accuracy check, weekly feature refresh, monthly retraining

---

## SUCCESS CRITERIA

- AI Assistant on every page (floating orb, 4 tabs)
- Logo in header/footer
- Neural predictions: cash flow, churn, PNR overrun, fraud
- Human feedback loop
- Gen_Led transformed (4,342 GL entries)
- 2023 data ingested
- IHE-ERP nightly sync
- Orphans < 5%
- All tests pass (250+)
- Docker builds
- GitHub updated
