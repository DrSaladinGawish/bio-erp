# ═══════════════════════════════════════════════════════════════════
# SYSTEM READY CHECKLIST — Pre-SCM Cost Engine
# Verify all requirements balanced before next stage
# ═══════════════════════════════════════════════════════════════════

## A. FILES INVENTORY (All 7 confirmed in /mnt/agents/output/)

| # | File | Status | Action Required |
|---|------|--------|-----------------|
| 1 | scm_bio_bridge_hardened.py | ✅ Ready | Copy to app/scm_bridge/ replacing old |
| 2 | scm_staging_schema.sql | ✅ Ready | Run against PostgreSQL bio_erp DB |
| 3 | backup_service_fernet_fix.py | ✅ Ready | Patch into backup_service.py |
| 4 | presentation_path_traversal_fix.py | ✅ Ready | Patch into presentation_engine.py |
| 5 | requirements_missing_packages.txt | ✅ Ready | Append to requirements.txt |
| 6 | PG_INTEGRATION_TEST_FIX.md | ✅ Ready | Follow for integration test setup |
| 7 | mount_scm_bridge.py | ✅ Ready | Apply patch to main.py |

## B. REQUIREMENTS BALANCE CHECK

### B1. Python Packages (Append to requirements.txt)
```
cryptography>=42.0.0
boto3>=1.34.0
azure-storage-blob>=12.19.0
httpx>=0.27.0
```
Install: pip install -r requirements.txt
Status: ⬜ NOT YET DONE (user must run)

### B2. PostgreSQL Staging Schema
```bash
psql -h localhost -U postgres -d bio_erp -f scm_staging_schema.sql
```
Creates: scm_staging.cost_analysis, vendor_scorecards, budget_forecasts, promotion_requests
Status: ⬜ NOT YET DONE (Docker Desktop unavailable, use local PG)

### B3. Environment Variables (Add to .env)
```env
PRODUCTION_DB_URL=postgresql://postgres:postgres123@localhost:5432/bio_erp
STAGING_DB_URL=postgresql://postgres:postgres123@localhost:5432/bio_erp
SCM_STAGING_SCHEMA=scm_staging
FERNET_KEY=          # Leave empty for auto-generation, or set fixed key
```
Status: ⬜ NOT YET DONE (user must configure)

## C. CODE PATCHES REQUIRED

### C1. Replace scm_bio_bridge.py
```bash
copy /mnt/agents/output/scm_bio_bridge_hardened.py      D:\ERP System\BIO_ERP\app\scm_bridge\scm_bio_bridge.py
```
Changes from dev version:
- + require_permission() on all 10 endpoints
- + ALLOWED_STAGING_TABLES whitelist (SQL injection fix)
- + _validate_table_name() regex guard
- + Pydantic field_validator on PromotionRequest.staging_table
- + Fallback rbac import for organ dev mode
Status: ⬜ NOT YET DONE

### C2. Patch backup_service.py (Fernet key persistence)
```python
# REPLACE this line in backup_service.py:
#     self.fernet = Fernet(Fernet.generate_key())
# WITH:
from .backup_service_fernet_fix import get_fernet
self.fernet = get_fernet()
```
Status: ⬜ NOT YET DONE

### C3. Patch presentation_engine.py (Path traversal)
```python
# REPLACE download endpoint:
#     @router.get("/download/{filename}")
#     def download(filename: str):
#         path = os.path.join(UPLOADS_DIR, filename)
#         return FileResponse(path)
# WITH:
from .presentation_path_traversal_fix import safe_file_path
@router.get("/download/{filename}")
def download(filename: str):
    path = safe_file_path(filename)
    return FileResponse(path)
```
Status: ⬜ NOT YET DONE

### C4. Mount SCM bridge in main.py
```python
# Add to app/main.py:
from app.scm_bridge.scm_bio_bridge import router as scm_bridge_router
app.include_router(scm_bridge_router, prefix="/api/v1/scm")
```
Status: ⬜ NOT YET DONE

## D. TEST VERIFICATION STEPS

### D1. Organ Dev Tests (SQLite, port 8001) — MUST PASS
```bash
cd "D:\ERP System\BIO_ERP"
pytest tests/ -v
Expected: 178 tests pass, 0 failures
```
Status: ⬜ NOT YET VERIFIED (run after patches applied)

### D2. SCM Bridge Specific Tests (NEW)
```bash
pytest tests/test_scm_bridge.py -v
Expected:
  - test_read_events_auth_blocked (no token = 403)
  - test_read_events_with_token (token = 200)
  - test_sql_injection_blocked (bad table name = 400)
  - test_promotion_requires_admin (user token = 403, admin token = 200)
  - test_staging_write_no_production_mutation
```
Status: ⬜ NOT YET GENERATED (will provide with cost engine)

### D3. Root App Integration Tests (PostgreSQL, port 8000)
```bash
pytest tests/integration/ -v
Expected: All endpoints reachable under /api/v1/scm/scm-bridge/
```
Status: ⬜ NOT YET DONE (requires PostgreSQL + DDL)

## E. SECURITY GAPS CLOSED

| Gap | Original Risk | Fix Applied | Verified |
|-----|-------------|-------------|----------|
| SCM unguarded endpoints | Anyone reads/writes production | require_permission() on all 10 routes | ⬜ |
| SQL injection in approve_promotion | Arbitrary SQL execution | ALLOWED_STAGING_TABLES whitelist + regex | ⬜ |
| Backup Fernet random key | Backups unrecoverable after restart | Persistent key (env → file → generate+save) | ⬜ |
| Presentation path traversal | File system escape via filename | sanitize_filename() + directory boundary check | ⬜ |

## F. BLOCKED ITEMS & WORKAROUNDS

| Blocked Item | Reason | Workaround |
|-------------|--------|------------|
| Docker Desktop | Not available | Use local PostgreSQL 15+ |
| docker_sync.py | Docker unavailable | Manual psql execution of DDL |
| import_docker_to_pg.py | Docker unavailable | Direct CSV import via psql COPY |
| cryptography package | Not in requirements.txt | pip install cryptography>=42.0.0 |
| boto3/azure-storage-blob | Not in requirements.txt | pip install (only if cloud backup used) |
| httpx | Not in requirements.txt | pip install httpx>=0.27.0 |

## G. SCM COST ENGINE PREREQUISITES

Before generating strategic cost analysis engine, the following MUST be green:

| Prerequisite | Status | Blocking? |
|-------------|--------|-----------|
| Hardened bridge deployed | ⬜ | YES — engine feeds into bridge |
| Staging schema created | ⬜ | YES — engine writes to staging tables |
| 178 tests still pass | ⬜ | YES — no regressions allowed |
| PostgreSQL accessible | ⬜ | NO — engine can run in-memory for dev |
| rbac permissions defined | ⬜ | PARTIAL — fallback exists in hardened bridge |

## H. RECOMMENDED EXECUTION ORDER

1. ⬜ Append requirements.txt → pip install
2. ⬜ Apply code patches (C1-C4)
3. ⬜ Run 178 organ tests → confirm pass
4. ⬜ Install local PostgreSQL (if not present)
5. ⬜ Run scm_staging_schema.sql
6. ⬜ Configure .env variables
7. ⬜ Start root app on port 8000
8. ⬜ Run integration tests
9. ✅ GENERATE SCM COST ENGINE (next stage)

## I. QUICK VERIFICATION COMMAND (Windows PowerShell)

```powershell
# Check all files exist
$files = @(
    "app/scm_bridge/scm_bio_bridge_hardened.py",
    "scripts/scm_staging_schema.sql",
    "app/backup/backup_service_fernet_fix.py",
    "app/presentation/presentation_path_traversal_fix.py",
    "requirements.txt"
)
foreach ($f in $files) { if (Test-Path $f) { "✅ $f" } else { "❌ MISSING: $f" } }

# Check packages installed
python -c "import cryptography; print('cryptography:', cryptography.__version__)"
python -c "import httpx; print('httpx:', httpx.__version__)"
python -c "import boto3; print('boto3:', boto3.__version__)"

# Check PostgreSQL
psql -U postgres -d bio_erp -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'scm_staging';"
```

═══════════════════════════════════════════════════════════════════
CURRENT STATUS: 7/7 files generated, 0/9 prerequisites completed
NEXT ACTION: User applies patches → confirms 178 tests pass → generates cost engine
═══════════════════════════════════════════════════════════════════
