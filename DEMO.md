# BIO_ERP v5 — Stakeholder Demo Walkthrough

## Prerequisites
- Server running on `http://localhost:8000`
- Swagger UI at `http://localhost:8000/docs`

## Demo Flow (10 minutes)

### 1. Health Check (30 sec)
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"ok","version":"5.1.0","database":"ok"}`

### 2. Root Endpoint (30 sec)
```bash
curl http://localhost:8000/
```
Expected: `{"message":"BIO_ERP v5","version":"5.1.0"}`

### 3. Login & Get Token (1 min)
```bash
curl -X POST http://localhost:8000/api/v1/accounting/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```
Save the returned `access_token`.

### 4. Chart of Accounts (2 min)
Show the full CoA tree:
```bash
curl http://localhost:8000/api/v1/accounting/coa?category_id=1 \
  -H "Authorization: Bearer <token>"
```
Point out: category hierarchy, account codes, active/inactive flags.

### 5. Ledger Inquiry (2 min)
```bash
curl http://localhost:8000/api/v1/accounting/ledger-entries?account_id=1&page=1&page_size=10 \
  -H "Authorization: Bearer <token>"
```
Explain: pagination (`page`, `page_size`), date filtering (`date_from`, `date_to`), debit/credit balance.

### 6. Create Ledger Entry (2 min)
```bash
curl -X POST http://localhost:8000/api/v1/accounting/ledger-entries \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"account_id":1,"entry_type":"debit","amount":1000.00,"description":"Demo entry","category_id":1}'
```
Show: 201 Created, Pydantic validation errors on bad data.

### 7. Auth Enforcement (1 min)
```bash
curl http://localhost:8000/api/v1/accounting/coa?category_id=1
```
Expected: `401` JSON — proves all endpoints are protected.

### 8. Swagger UI (1 min)
Open `http://localhost:8000/docs` — show interactive testing.

## Key Talking Points
- **6 database models** live: Users, ChartOfAccounts, Categories, LedgerEntries, Journals, Documents
- **7 REST endpoints** — full CRUD on ledger-entries + paginated inquiry + CoA tree
- **Auth** — JWT bearer tokens, admin seed, 401 enforcement
- **Validation** — Pydantic v2 with `model_config = SettingsConfigDict`
- **32 automated tests** passing with zero warnings
