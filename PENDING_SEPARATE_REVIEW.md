# Pending Separate Review

These fixes were identified during the SQL injection audit but are out of scope
for this pass. They are legitimate improvements that should be reviewed and
applied separately.

## 1. copilot/engine.py — Undefined `TfidfVectorizer` + unused imports

**File:** `ERP System/BIO_ERP/app/copilot/engine.py`

**Issues:**
- `_get_vectorizer()` references `TfidfVectorizer` without importing it at the
  method level (line ~111). If sklearn is installed, this will raise
  `NameError` at runtime when the TF-IDF path is triggered.
- Unused imports: `dataclass`, `field` (from `dataclasses`), `re`, `json`,
  `hashlib`, `Path` — all importable but never referenced in the file body.
  Ruff flags these as F401.

**Fix:** Add `from sklearn.feature_extraction.text import TfidfVectorizer` to
`_get_vectorizer()`, remove unused top-level imports.

**Risk:** Low. The TfidfVectorizer fix prevents a runtime crash. Import
removal is safe — confirmed no external consumers import from this module.

## 2. services/vibe_code_generator.py — Undefined `file_path` + unsafe `/tmp/`

**File:** `ERP System/BIO_ERP/app/services/vibe_code_generator.py`

**Issues:**
- `_validate_syntax()` writes to `f"/tmp/{os.path.basename(file_path)}"` but
  `/tmp/` doesn't exist on Windows and is a security concern on Linux
  (symlink attacks, predictable paths).
- `Tuple` imported from `typing` but never used (F401).

**Fix:** Replace with `tempfile.NamedTemporaryFile()`, remove unused `Tuple`.

**Risk:** Low-Medium. The `/tmp/` path is only used during code generation
validation, not in production query execution. But it breaks on Windows.

## 3. copilot/event_assistant.py — Bare `except:` clause

**File:** `ERP System/BIO_ERP/app/copilot/event_assistant.py:224`

**Issue:** Bare `except:` in date parsing catches `KeyboardInterrupt`,
`SystemExit`, `MemoryError` etc. Should be `except (ValueError, TypeError):`.

**Risk:** Low. Only triggered during event risk assessment date parsing.

## 4. organs/incentivehouse_organ/sub_app.py — Bare `except:` clause

**File:** `ERP System/BIO_ERP/app/organs/incentivehouse_organ/sub_app.py:509`

**Issue:** Bare `except:` in legacy event creation date parsing. Same concern
as #3 above.

**Risk:** Low-Medium. This is in a production endpoint (`/events/create`)
but only affects the date duration calculation.

## 5. AGENTS.md — Project root documentation

**File:** `AGENTS.md` (project root)

**Issue:** Created during the audit session. Contains dev commands (ruff, bandit,
pytest) and project conventions.

**Action:** Review whether this file is useful. If yes, recreate it as a
deliberate decision. If not, leave deleted.
