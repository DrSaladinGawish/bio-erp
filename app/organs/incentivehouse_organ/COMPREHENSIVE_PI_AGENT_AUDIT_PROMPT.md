ROLE: Comprehensive System Auditor for IncentiveHouse ERP
TASK: Conduct a complete, verified assessment of EVERY module, function, UI element, and requirement
CONSTRAINTS:
  - ONLY report what you can VERIFY by reading files on disk
  - NO assumptions, NO "I believe", NO hallucination
  - If a file doesn't exist, say "NOT FOUND"
  - If you can't verify something, say "UNVERIFIED"
  - Use PROBLEM/EVIDENCE/VERDICT format with tables
  - Take screenshots where possible

═══════════════════════════════════════════════════════════════════════════════
SECTION 1: SYSTEM IDENTITY & INFRASTRUCTURE
═══════════════════════════════════════════════════════════════════════════════

1.1 Base Path Verification
  - Check D:\ERP System\BIO_ERP\ exists
  - List top-level directory contents
  - Check for app/, tests/, data/, docs/, launcher/ directories
  - VERDICT: EXISTS / NOT FOUND

1.2 Version & Git History
  - Check .git/ exists
  - Run: git log --oneline | head -20
  - Count total commits
  - Check current branch
  - VERDICT: COMMIT_COUNT / BRANCH / LAST_COMMIT_DATE

1.3 Infrastructure Files
  Check each:
  - requirements.txt (list key packages: fastapi, uvicorn, sqlalchemy, etc.)
  - .gitignore
  - .env.example
  - Dockerfile
  - docker-compose.yml
  - nginx.conf
  - docker-compose-remote.yml
  VERDICT: EXISTS (line count) / NOT FOUND

1.4 Environment Configuration
  - Check .env file exists (not .env.example)
  - List all variables (mask secrets)
  - Check DATABASE_URL format
  - Check PORT setting
  VERDICT: CONFIGURED / MISSING_VARS

═══════════════════════════════════════════════════════════════════════════════
SECTION 2: DATABASE & ORM (ALL TABLES)
═══════════════════════════════════════════════════════════════════════════════

2.1 Database Connection
  - Find DB file (app.db, bio_erp.db, etc.) or check PostgreSQL connection
  - Test connection: python -c "from app.database import engine; print(engine)"
  VERDICT: CONNECTED / FAILED

2.2 Table Inventory
  Run: python -c "
  from sqlalchemy import inspect
  from app.database import engine
  inspector = inspect(engine)
  tables = inspector.get_table_names()
  print(f'TOTAL_TABLES: {len(tables)}')
  for t in sorted(tables): print(f'  - {t}')
  "
  VERDICT: TABLE_COUNT / TABLE_LIST

2.3 Required Tables Check
  Check if these exist (from requirements):
  - clients, vendors, cost_centers, pnr_dim, events, work_orders
  - sales_line_items, bnk_transactions, sales_invoices, purchase_orders
  - event_line_items, staff_assignments, vendor_invoices, audit_trail
  - bnk_reconciliation, mv_event_financial_summary
  - ChartOfAccounts, Employee, JournalVoucher, Bank
  - IHEClient, IHEVendor, PurchaseVoucher, PNRMaster
  - ServiceMainCategory, ServiceSubCategory, ServiceType
  - PNRBudgetLineItem, SalesInvoice, SalesLineItem
  VERDICT: FOUND / MISSING for each

2.4 Data Verification
  - Check if bank_transactions has data: SELECT COUNT(*) FROM bank_transactions
  - Check if events has data
  - Check if clients has data
  VERDICT: ROW_COUNT for each table

═══════════════════════════════════════════════════════════════════════════════
SECTION 3: BACKEND MODULES & ROUTERS (ALL API ENDPOINTS)
═══════════════════════════════════════════════════════════════════════════════

3.1 Main Application
  - Check app/main.py exists
  - List all include_router() calls
  - Check for app creation: app = FastAPI()
  VERDICT: ROUTERS_MOUNTED / LIST

3.2 OR-ERP Module (Operational Research)
  - Check app/organs/or_organ/ exists
  - List all .py files
  - Check for 12 engine classes
  - Check for 19 API endpoints
  - Verify mounted at /api/v1/or/
  VERDICT: FILE_COUNT / ENGINE_COUNT / ENDPOINT_COUNT

3.3 IncentiveHouse Organ
  - Check app/organs/incentivehouse_organ/ exists
  - List all .py files
  - Check models/ihe_models.py exists
  - Check routers/ directory
  - Verify mounted at /api/v1/incentivehouse/ or /api/v1/ih/
  VERDICT: FILE_COUNT / ROUTER_COUNT

3.4 EventCore Bridge
  - Check app/routers/eventcore_bridge.py exists
  - Check if EventCore routes are mounted
  - Verify bridge receiver code
  VERDICT: EXISTS / NOT_FOUND / INTEGRATED

3.5 SCM Module
  - Check D:\SCM Module\ exists
  - List files
  - Check if mounted in Bio-ERP
  VERDICT: EXISTS (file_count) / MOUNTED / STANDALONE

3.6 Sales Module
  - Check sales router exists
  - Verify endpoints:
    - GET /api/v1/categories
    - GET /api/v1/categories/{name}
    - POST /api/v1/categories
    - POST /api/v1/categories/{name}/sub-categories
    - GET /api/v1/sub-categories
    - GET /api/v1/jobs/{id}/line-items
  VERDICT: ENDPOINT_COUNT / LIST

3.7 Auth & Admin Module
  - Check auth router exists
  - Check admin router exists
  - Verify JWT implementation
  - Check for role-based permissions (admin, user, readonly)
  - Verify default users exist (admin/user)
  VERDICT: AUTH_TYPE / ROLE_COUNT / USER_COUNT

3.8 All Routes Inventory
  Start server and fetch:
  curl http://localhost:9001/openapi.json
  Count total paths
  List ALL paths by category:
  - /api/v1/auth/*
  - /api/v1/admin/*
  - /api/v1/or/*
  - /api/v1/incentivehouse/* or /api/v1/ih/*
  - /api/v1/scm/*
  - /api/v1/categories/*
  - /api/v1/events/*
  - /api/v1/bnk/*
  - /api/v1/gl/*
  - /api/v1/documents/*
  - /api/v1/reports/*
  VERDICT: TOTAL_ROUTES / PER_CATEGORY

═══════════════════════════════════════════════════════════════════════════════
SECTION 4: FRONTEND & UI (ALL TEMPLATES)
═══════════════════════════════════════════════════════════════════════════════

4.1 Template Directory
  - Check app/templates/ exists
  - List ALL .html files
  VERDICT: FILE_COUNT / FILE_LIST

4.2 Dashboard
  - Check dashboard.html or index.html exists
  - Verify contains: dark header, world map background, sidebar
  - Verify contains: module cards (Dashboard, Analysis, Sales, Purchase, Events, Operation, Employees, Accounts, Preferences)
  - Verify contains: status panel with online indicators
  - Verify contains: user name input, logout button
  VERDICT: EXISTS / MISSING_ELEMENTS

4.3 Event Form
  - Check event_form.html or events.html exists
  - Verify fields:
    - CoCen_Key_ID
    - PNR_ID
    - Branch
    - Client_ID
    - Currency_ID
    - Conversion_Rate
    - Event_Description
    - Start_Date, End_Date
    - Size, Location, Avenue
    - Payment_Terms
    - Requester
    - Gross_Sales
    - PO_COPY upload
    - POST/Save buttons
    - Sales Line Items subform grid
  VERDICT: EXISTS / FIELD_COUNT / MISSING_FIELDS

4.4 Bank Reconciliation Form
  - Check bank_recon.html or bank_recon_form.html exists
  - Verify 5-step protocol: Extract → Validate → Stage → Reconcile → Promote
  - Verify contains: summary cards, check book tabs, recon grid
  - Verify contains: Smart Recon button
  - Verify contains: Export Excel/CSV buttons
  - Verify contains: Promote to Production button
  - Verify contains: sub-ledger/type/keyword input fields
  VERDICT: EXISTS / FEATURE_COUNT / MISSING_FEATURES

4.5 Login Page
  - Check login.html exists
  - Verify: username field, password field, login button
  - Verify: company logo
  VERDICT: EXISTS / ELEMENTS

4.6 AI Smart Window
  - Check if AI window is embedded in base template
  - Verify: "IHE AI" or similar branding
  - Verify: chat input, send button
  - Verify: appears on all forms
  VERDICT: EMBEDDED / STANDALONE / MISSING

4.7 Company Logo
  - Check app/static/logo.ico or logo.png exists
  - Verify referenced in header
  - Verify referenced in footer
  VERDICT: HEADER / FOOTER / BOTH / MISSING

4.8 CSS/JS Assets
  - Check app/static/erp-theme.css exists
  - Check app/static/ has JS files
  - Verify dark theme colors
  VERDICT: CSS_EXISTS / JS_EXISTS

═══════════════════════════════════════════════════════════════════════════════
SECTION 5: DATA SOURCES & IMPORT
═══════════════════════════════════════════════════════════════════════════════

5.1 Excel Files
  Check exact paths:
  - Bnk_TRNX SOURCE.xlsx (2,501 transactions)
  - Bnk_Trnx_Sub_Key.xlsx
  - Data_Base_Mtbls.xlsx (13 sheets, 1,751 records)
  Report: EXISTS (path, size) / NOT_FOUND

5.2 Data Import Scripts
  - Check extraction_engine.py exists
  - Check import_data.py exists
  - Verify extract_bank_transactions() function
  - Verify master data loader
  VERDICT: EXISTS / FUNCTIONS_FOUND

5.3 Data Load Status
  Run: python -c "
  from app.database import SessionLocal
  from app.models import BankTransaction
  db = SessionLocal()
  count = db.query(BankTransaction).count()
  print(f'BankTransaction rows: {count}')
  "
  VERDICT: LOADED (row_count) / EMPTY / SCRIPT_ERROR

═══════════════════════════════════════════════════════════════════════════════
SECTION 6: TESTS & QUALITY
═══════════════════════════════════════════════════════════════════════════════

6.1 Test Suite
  - Count test files: tests/test_*.py
  - Run: pytest tests/ --co -q (collect only)
  - Report: FILE_COUNT / TEST_COUNT

6.2 Test Execution
  Run: pytest tests/ -v --tb=short
  Report: PASSED / FAILED / SKIPPED / TIME

6.3 Regression Tests
  - Check tests/test_regression_known_issues.py exists
  - Verify 4 fragile areas covered
  VERDICT: EXISTS / TEST_COUNT

6.4 Quality Gate
  - Check ih_erp_quality_gate_v2.py exists
  - Run: python ih_erp_quality_gate_v2.py
  Report: SCORE / PASS_COUNT / FAIL_COUNT

═══════════════════════════════════════════════════════════════════════════════
SECTION 7: DEPLOYMENT & RUNTIME
═══════════════════════════════════════════════════════════════════════════════

7.1 Server Status
  - Check port 8000: Get-NetTCPConnection -LocalPort 8000
  - Check port 8001: Get-NetTCPConnection -LocalPort 8001
  - Check port 9001: Get-NetTCPConnection -LocalPort 9001
  VERDICT: PORT_8000 / PORT_8001 / PORT_9001

7.2 Desktop Launcher
  - Check launcher/ directory exists
  - Check Start-IH-ERP.bat exists
  - Check Start-IH-ERP.ps1 exists
  - Check desktop shortcut exists
  VERDICT: EXISTS / SHORTCUT_CREATED

7.3 Docker
  - Check Docker Desktop installed
  - Check image built: docker images | findstr incentivehouse
  - Check docker-compose-remote.yml exists
  VERDICT: INSTALLED / IMAGE_BUILT / COMPOSE_EXISTS

7.4 Firewall
  - Check port 9001 open: Get-NetFirewallRule -DisplayName "IH-ERP*"
  - Check port 80 open
  VERDICT: PORT_9001 / PORT_80

═══════════════════════════════════════════════════════════════════════════════
SECTION 8: INTEGRATION & UNIFICATION
═══════════════════════════════════════════════════════════════════════════════

8.1 EventCore Integration
  - Check if EventCore routes mounted in Bio-ERP
  - Check for eventcore_bridge.py imports in main.py
  - Verify /eventcore/ prefix exists in routes
  VERDICT: INTEGRATED / SEPARATE

8.2 OR-ERP Integration
  - Verify /api/v1/or/ accessible
  - Check OR docs at /api/v1/or/docs
  VERDICT: MOUNTED / ACCESSIBLE

8.3 SCM Integration
  - Verify /api/v1/scm/ accessible
  - Check SCM staging tables exist
  VERDICT: MOUNTED / ACCESSIBLE

8.4 Single Database
  - Verify all modules use same DB connection
  - Check for multiple DB files
  VERDICT: SINGLE / MULTIPLE

═══════════════════════════════════════════════════════════════════════════════
SECTION 9: REQUIREMENTS COMPLIANCE (FROM ORIGINAL SPEC)
═══════════════════════════════════════════════════════════════════════════════

Check each original requirement:

9.1 AI Smart Window
  - Embedded in all forms? Check base template
  - Context-aware? Check JS code
  VERDICT: YES / NO

9.2 Company Logo
  - Header? Check base template
  - Footer? Check base template
  VERDICT: HEADER / FOOTER / BOTH / NEITHER

9.3 Smart Presentation
  - Dashboard has intelligent layout?
  - Auto-refresh? Check JS
  VERDICT: YES / NO

9.4 Easy to Use
  - Sidebar navigation?
  - Clear labels?
  VERDICT: YES / NO

9.5 Neural Nodes
  - Visual indicators in UI?
  - Check CSS/JS for neural network graphics
  VERDICT: YES / NO

9.6 Document Management
  - PO_COPY upload in event form?
  - Document list in /documents?
  VERDICT: YES / NO

9.7 ERP Builder Protocol Compliance
  - P0 (Auth, Variance, Audit, Backup) — check each
  - P1, P2, P3 — check documentation
  VERDICT: COMPLIANT / GAPS

═══════════════════════════════════════════════════════════════════════════════
FINAL OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

For EACH section above, provide:

PROBLEM: What you were checking
EVIDENCE: Exact file paths, command outputs, counts, errors
VERDICT: PASS / FAIL / PARTIAL / NOT_FOUND / UNVERIFIED

FINAL EXECUTIVE SUMMARY TABLE:

| Section | Status | Score | Key Finding |
|---------|--------|-------|-------------|
| 1. Infrastructure | ? | ? | ? |
| 2. Database | ? | ? | ? |
| 3. Backend | ? | ? | ? |
| 4. Frontend | ? | ? | ? |
| 5. Data | ? | ? | ? |
| 6. Tests | ? | ? | ? |
| 7. Deployment | ? | ? | ? |
| 8. Integration | ? | ? | ? |
| 9. Requirements | ? | ? | ? |

OVERALL SCORE: X/9 sections PASS

RECOMMENDATION:
  - ONE concrete next action
  - No multi-step plans
  - No "it depends"
  - Format: "Do X to achieve Y"
