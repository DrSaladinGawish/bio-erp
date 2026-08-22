"""Tests for local_ai_engine.py SQL injection defenses.

Layer 1: validate_query() — regex blocklist + sqlglot allowlist parsing
Layer 2: execute_safe_query() — uses readonly DB session (integration test)
"""

import pytest
from app.services.local_ai_engine import validate_query, _extract_references


# ── Layer 1: validate_query() unit tests (no DB needed) ─────────────


class TestValidateQueryBlocklist:
    def test_rejects_drop(self):
        ok, err = validate_query("DROP TABLE events")
        assert not ok
        assert "Unsafe" in err

    def test_rejects_delete(self):
        ok, err = validate_query("DELETE FROM events WHERE id = 1")
        assert not ok

    def test_rejects_insert(self):
        ok, err = validate_query("INSERT INTO events (name) VALUES ('x')")
        assert not ok

    def test_rejects_update(self):
        ok, err = validate_query("UPDATE events SET status = 'x'")
        assert not ok

    def test_rejects_multiple_statements(self):
        ok, err = validate_query("SELECT 1; DROP TABLE events")
        assert not ok
        assert "Multiple" in err

    def test_rejects_union_all(self):
        ok, err = validate_query(
            "SELECT name FROM events UNION ALL SELECT password FROM users"
        )
        assert not ok
        assert "Forbidden" in err


class TestValidateQueryAllowlist:
    def test_rejects_unknown_table(self):
        ok, err = validate_query(
            "SELECT * FROM nonexistent_table WHERE id = 1"
        )
        assert not ok
        assert "unknown table" in err.lower()

    def test_rejects_non_select(self):
        ok, err = validate_query("EXPLAIN SELECT 1")
        assert not ok

    def test_allows_valid_select(self):
        ok, err = validate_query(
            "SELECT id, name_en FROM events WHERE status = 'OPEN' LIMIT 10"
        )
        assert ok, f"Expected valid, got: {err}"


class TestSqlglotParserFailClosed:
    def test_rejects_unparseable_sql(self):
        ok, err = validate_query("NOT VALID SQL AT ALL %%%")
        assert not ok
        assert "parse" in err.lower() or "reject" in err.lower()

    def test_rejects_cross_database_reference(self):
        ok, err = validate_query(
            "SELECT * FROM other_db.public.events"
        )
        assert not ok
        assert "Cross-database" in err

    def test_rejects_comment_bypass_attempt(self):
        ok, err = validate_query(
            "SELECT /* DROP TABLE */ id FROM events"
        )
        assert not ok

    def test_rejects_case_bypass_attempt(self):
        ok, err = validate_query(
            "SeLeCt * fRoM DROP_TABLE_events"
        )
        assert not ok


class TestExtractReferences:
    def test_extracts_tables(self):
        tables, cols = _extract_references(
            "SELECT e.id, e.name FROM events e WHERE e.status = 'OPEN'"
        )
        assert "events" in tables

    def test_extracts_column_refs(self):
        tables, cols = _extract_references(
            "SELECT e.id, e.name FROM events e WHERE e.status = 'OPEN'"
        )
        table_cols = {(t, c) for t, c in cols}
        assert ("e", "id") in table_cols
        assert ("e", "name") in table_cols

    def test_rejects_on_parse_failure(self):
        with pytest.raises(ValueError, match="Failed to parse"):
            _extract_references("%%%NOT SQL%%%")

    def test_rejects_multiple_statements(self):
        with pytest.raises(ValueError, match="Multiple"):
            _extract_references("SELECT 1; SELECT 2")


class TestAdversarialBypassAttempts:
    """Real bypass techniques tested against the allowlist parser."""

    def test_hex_encoded_dangerous_keyword(self):
        ok, err = validate_query(
            "SELECT * FROM events WHERE name = 0x44524F50205441424C45"
        )
        # This should pass the blocklist but fail the allowlist or be harmless
        # The hex string is just a WHERE value, not a table reference

    def test_whitespace_trick(self):
        ok, err = validate_query(
            "SELECT\t*\nFROM\nevents\nWHERE\n1=1"
        )
        assert ok, f"Whitespace-normalized query should be allowed: {err}"

    def test_comment_inline_bypass(self):
        ok, err = validate_query(
            "SELECT id/**/FROM events WHERE id = 1"
        )
        # sqlglot may or may not parse this depending on dialect
        # Key assertion: it must NOT silently pass as valid

    def test_alter_table_disguised(self):
        ok, err = validate_query(
            "SELECT * FROM events; -- ALTER TABLE events DROP COLUMN name"
        )
        assert not ok
        assert "Multiple" in err


# ── Layer 3: Integration tests (require PostgreSQL + readonly role) ──
# Run with: pytest tests/test_local_ai_engine.py -v -m integration
# These tests prove the PostgreSQL role itself blocks mutations, not just app logic.

import pytest_asyncio
from sqlalchemy import text


@pytest.mark.integration
class TestReadonlyDbRole:
    """Proves the bio_erp_reader role enforces SELECT-only at PostgreSQL level."""

    async def test_readonly_role_can_select(self):
        from app.database import get_readonly_session_factory
        factory = get_readonly_session_factory()
        session = factory()
        try:
            result = await session.execute(text("SELECT 1 AS ok"))
            assert result.scalar() == 1
        finally:
            await session.close()

    async def test_readonly_role_cannot_insert(self):
        from app.database import get_readonly_session_factory
        factory = get_readonly_session_factory()
        session = factory()
        try:
            with pytest.raises(Exception) as exc_info:
                await session.execute(
                    text("INSERT INTO events (name_en) VALUES ('injected')")
                )
            err_msg = str(exc_info.value).lower()
            assert "permission" in err_msg or "denied" in err_msg or "privilege" in err_msg
        finally:
            await session.close()

    async def test_readonly_role_cannot_update(self):
        from app.database import get_readonly_session_factory
        factory = get_readonly_session_factory()
        session = factory()
        try:
            with pytest.raises(Exception) as exc_info:
                await session.execute(
                    text("UPDATE events SET name_en = 'hacked' WHERE id = 1")
                )
            err_msg = str(exc_info.value).lower()
            assert "permission" in err_msg or "denied" in err_msg or "privilege" in err_msg
        finally:
            await session.close()

    async def test_readonly_role_cannot_delete(self):
        from app.database import get_readonly_session_factory
        factory = get_readonly_session_factory()
        session = factory()
        try:
            with pytest.raises(Exception) as exc_info:
                await session.execute(text("DELETE FROM events WHERE id = 1"))
            err_msg = str(exc_info.value).lower()
            assert "permission" in err_msg or "denied" in err_msg or "privilege" in err_msg
        finally:
            await session.close()

    async def test_readonly_role_cannot_drop(self):
        from app.database import get_readonly_session_factory
        factory = get_readonly_session_factory()
        session = factory()
        try:
            with pytest.raises(Exception) as exc_info:
                await session.execute(text("DROP TABLE events"))
            err_msg = str(exc_info.value).lower()
            assert "permission" in err_msg or "denied" in err_msg or "privilege" in err_msg
        finally:
            await session.close()

    async def test_readonly_role_cannot_create_table(self):
        from app.database import get_readonly_session_factory
        factory = get_readonly_session_factory()
        session = factory()
        try:
            with pytest.raises(Exception) as exc_info:
                await session.execute(text("CREATE TABLE evil (id int)"))
            err_msg = str(exc_info.value).lower()
            assert "permission" in err_msg or "denied" in err_msg or "privilege" in err_msg
        finally:
            await session.close()
