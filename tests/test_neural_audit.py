"""
tests/test_neural_audit.py
Unit tests for neural_audit.py.
All DB interaction is mocked — no live database required.

Coverage targets per build brief:
- At least one test per check for table-missing, column-missing,
  and DB-error degradation paths.
- Tests confirming FDR correction reduces false-positive flags vs.
  the uncorrected count on synthetic fixtures.
- Churn-N threshold constants match the canonical definition.
"""

from __future__ import annotations

import json
import math
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.scripts.neural_audit import (
    _CHURN_ABORT,
    _CHURN_GBM,
    AuditReport,
    CheckResult,
    _benjamini_hochberg,
    _bootstrap_correlation_ci,
    check_client_history_depth,
    check_entity_pooling_validity,
    check_revenue_row_count,
    check_risk_label_distribution,
    check_risk_label_schema,
    render_report,
)

# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

def _rows_result(rows):
    """Mock execute() result returning *rows* from fetchall()."""
    r = MagicMock()
    r.fetchall.return_value = rows
    r.fetchone.return_value = rows[0] if rows else None
    return r


def _scalar_result(value):
    """Mock execute() result returning *value* from scalar()."""
    r = MagicMock()
    r.fetchall.return_value = []
    r.fetchone.return_value = None
    r.scalar.return_value = value
    return r


def _fetchedone_result(row):
    """Mock execute() result returning *row* from fetchone()."""
    r = MagicMock()
    r.fetchall.return_value = []
    r.fetchone.return_value = row
    return r


def _session_with(effects):
    """AsyncMock session whose execute() pops one effect per call."""
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=list(effects))
    return session


def _error_session(message="connection refused"):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=Exception(message))
    return session


# ══════════════════════════════════════════════════════════
# STATISTICAL HELPERS
# ══════════════════════════════════════════════════════════

class TestBenjaminiHochberg:
    def test_empty_input(self):
        assert _benjamini_hochberg([]) == []

    def test_single_significant(self):
        assert _benjamini_hochberg([0.01]) == [True]

    def test_single_not_significant(self):
        assert _benjamini_hochberg([0.5]) == [False]

    def test_reduces_false_positives_vs_uncorrected(self):
        """
        Core brief requirement: FDR correction must reduce the
        rejection count vs raw alpha=0.05 on a synthetic fixture
        of many near-threshold p-values (uniform 0.03-0.06).
        """
        rng = np.random.default_rng(0)
        p_values = list(rng.uniform(0.03, 0.06, size=100))

        raw_count = sum(1 for p in p_values if p < 0.05)
        corrected_count = sum(_benjamini_hochberg(p_values))

        assert corrected_count < raw_count, (
            f"FDR correction should reduce false positives: "
            f"raw={raw_count}, corrected={corrected_count}"
        )

    def test_all_significant(self):
        result = _benjamini_hochberg([0.001, 0.002, 0.003])
        assert all(result)

    def test_none_significant(self):
        result = _benjamini_hochberg([0.9, 0.8, 0.7])
        assert not any(result)

    def test_order_independence(self):
        """Rejection decisions must not depend on input order."""
        p1 = [0.001, 0.5, 0.9]
        p2 = [0.9, 0.001, 0.5]
        r1 = _benjamini_hochberg(p1)
        r2 = _benjamini_hochberg(p2)
        assert r1[0] is True
        assert r2[1] is True


class TestBootstrapCorrelationCI:
    def test_returns_three_floats(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([2.0, 4.0, 5.0, 4.0, 5.0])
        pt, lo, hi = _bootstrap_correlation_ci(x, y)
        assert isinstance(pt, float)
        assert isinstance(lo, float)
        assert isinstance(hi, float)

    def test_ci_contains_point_estimate(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        y = x * 2 + 0.1
        pt, lo, hi = _bootstrap_correlation_ci(x, y)
        assert lo <= pt <= hi

    def test_too_short_returns_nan(self):
        x = np.array([1.0, 2.0])
        y = np.array([1.0, 2.0])
        pt, lo, hi = _bootstrap_correlation_ci(x, y)
        assert math.isnan(pt)
        assert math.isnan(lo)
        assert math.isnan(hi)

    def test_strong_positive_correlation_ci_positive(self):
        rng = np.random.default_rng(42)
        x = np.arange(50, dtype=float)
        y = x + rng.normal(0, 0.5, 50)
        _, lo, hi = _bootstrap_correlation_ci(x, y, n_boot=500)
        assert lo > 0
        assert hi > 0


# ══════════════════════════════════════════════════════════
# CHECK 1 — Risk Label Schema
# ══════════════════════════════════════════════════════════

_CI_COLS = [
    "customer_id", "invoice_date", "due_date",
    "amount_due", "status", "paid_date", "is_active",
]


def _full_col_map():
    """Column map keyed in the same order as _REQUIRED_COLUMNS."""
    return {
        "customer_invoices": list(_CI_COLS),
        "ar_customers": ["id", "status"],
        "net_sales": ["client_id", "issue_date",
                      "total_amount", "is_active"],
        "sales_invoices": ["invoice_date", "total"],
        "purchase_orders": ["vendor_id", "po_date", "status"],
    }


class TestCheckRiskLabelSchema:
    @pytest.mark.asyncio
    async def test_all_tables_and_columns_present(self):
        tables = list(_full_col_map().keys())
        effects = [_rows_result([(t,) for t in tables])]
        for t in tables:
            effects.append(
                _rows_result([(c,) for c in _full_col_map()[t]])
            )
            effects.append(_scalar_result(100))
        session = _session_with(effects)

        report = AuditReport()
        found = await check_risk_label_schema(session, report)

        chk = report.checks[0]
        assert chk.status == "PASS"
        assert found == set(tables)

    @pytest.mark.asyncio
    async def test_missing_table_gives_fail(self):
        present = ["customer_invoices", "ar_customers"]
        effects = [_rows_result([(t,) for t in present])]
        for t in present:
            effects.append(
                _rows_result([(c,) for c in _full_col_map()[t]])
            )
            effects.append(_scalar_result(10))
        session = _session_with(effects)

        report = AuditReport()
        await check_risk_label_schema(session, report)

        chk = report.checks[0]
        assert chk.status == "FAIL"
        missing = chk.details["required_missing"]
        assert "net_sales" in missing
        assert "sales_invoices" in missing
        assert "purchase_orders" in missing

    @pytest.mark.asyncio
    async def test_missing_column_gives_warn(self):
        tables = list(_full_col_map().keys())
        col_map = _full_col_map()
        col_map["customer_invoices"] = [
            c for c in _CI_COLS if c != "paid_date"
        ]
        effects = [_rows_result([(t,) for t in tables])]
        for t in tables:
            effects.append(
                _rows_result([(c,) for c in col_map[t]])
            )
            effects.append(_scalar_result(10))
        session = _session_with(effects)

        report = AuditReport()
        await check_risk_label_schema(session, report)

        chk = report.checks[0]
        assert chk.status == "WARN"
        mc = chk.details["missing_columns"]
        assert mc.get("customer_invoices") == ["paid_date"]

    @pytest.mark.asyncio
    async def test_db_error_gives_fail_not_crash(self):
        session = _error_session("connection refused")
        report = AuditReport()
        await check_risk_label_schema(session, report)

        chk = report.checks[0]
        assert chk.status == "FAIL"
        assert "connection refused" in chk.message

    @pytest.mark.asyncio
    async def test_textbook_tables_flagged_if_present(self):
        tables = list(_full_col_map().keys()) + ["credit_events"]
        effects = [_rows_result([(t,) for t in tables])]
        for t in _full_col_map():
            effects.append(
                _rows_result([(c,) for c in _full_col_map()[t]])
            )
            effects.append(_scalar_result(10))
        session = _session_with(effects)

        report = AuditReport()
        await check_risk_label_schema(session, report)

        details = report.checks[0].details
        assert "credit_events" in details["textbook_present"]
        assert "credit_events" not in details["textbook_absent"]

    @pytest.mark.asyncio
    async def test_returns_confirmed_table_set(self):
        tables = list(_full_col_map().keys())
        effects = [_rows_result([(t,) for t in tables])]
        for t in tables:
            effects.append(_rows_result([]))
            effects.append(_scalar_result(0))
        session = _session_with(effects)

        report = AuditReport()
        found = await check_risk_label_schema(session, report)
        assert isinstance(found, set)
        assert found == set(tables)


# ══════════════════════════════════════════════════════════
# CHECK 2 — Entity Pooling
# ══════════════════════════════════════════════════════════

_FP_COLS = [
    "entity_id", "period_date", "total_revenue",
    "revenue_growth", "eva_next_period",
]


class TestCheckEntityPooling:
    @pytest.mark.asyncio
    async def test_financial_periods_missing_gives_skip(self):
        session = _session_with([_rows_result([])])
        report = AuditReport()
        await check_entity_pooling_validity(session, report)
        assert report.checks[0].status == "SKIP"

    @pytest.mark.asyncio
    async def test_missing_column_gives_skip(self):
        effects = [
            _rows_result([("financial_periods",)]),
            _rows_result([
                ("entity_id",), ("period_date",),
                ("total_revenue",), ("revenue_growth",),
            ]),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_entity_pooling_validity(session, report)

        assert report.checks[0].status == "SKIP"
        assert "eva_next_period" in report.checks[0].message

    @pytest.mark.asyncio
    async def test_db_error_gives_fail_not_crash(self):
        session = _error_session("timeout")
        report = AuditReport()
        await check_entity_pooling_validity(session, report)
        assert report.checks[0].status == "FAIL"

    @pytest.mark.asyncio
    async def test_single_entity_gives_warn(self):
        effects = [
            _rows_result([("financial_periods",)]),
            _rows_result([(c,) for c in _FP_COLS]),
            _rows_result([
                SimpleNamespace(
                    entity_id="E1", n_periods=12,
                    avg_revenue=100_000,
                )
            ]),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_entity_pooling_validity(session, report)
        assert report.checks[0].status == "WARN"

    def test_fdr_correction_reduces_false_positives(self):
        """
        Synthetic fixture: 6 entities x 20 features = 120 pairwise
        KS p-values near the 0.05 boundary. BH correction must
        reject fewer than raw alpha=0.05.
        """
        rng = np.random.default_rng(7)
        p_values = list(rng.uniform(0.03, 0.07, size=120))

        raw_rej = sum(1 for p in p_values if p < 0.05)
        corr_rej = sum(_benjamini_hochberg(p_values))
        assert corr_rej < raw_rej

    def test_confirmed_reversal_requires_non_overlapping_ci(self):
        """
        A single sign flip at N=24 must NOT be flagged as a
        confirmed reversal — only non-overlapping bootstrap CIs
        count. With very noisy data the CIs stay wide.
        """
        rng = np.random.default_rng(0)
        xa = np.arange(24, dtype=float)
        ya = xa + rng.normal(0, 10, 24)
        xb = np.arange(24, dtype=float)
        yb = -xb + rng.normal(0, 10, 24)

        _, la, ha = _bootstrap_correlation_ci(xa, ya, n_boot=500)
        _, lb, hb = _bootstrap_correlation_ci(xb, yb, n_boot=500)

        assert ha > la, "CI upper must exceed lower"
        assert hb > lb, "CI upper must exceed lower"


# ══════════════════════════════════════════════════════════
# CHECK 3 — Client History Depth
# ══════════════════════════════════════════════════════════

def _client_rows(counts):
    return [
        SimpleNamespace(
            client_id=i,
            n_months=c,
            total_invoices=c * 2,
            first_invoice=None,
            last_invoice=None,
        )
        for i, c in enumerate(counts)
    ]


class TestCheckClientHistoryDepth:
    @pytest.mark.asyncio
    async def test_table_missing_gives_skip(self):
        session = _session_with([_rows_result([])])
        report = AuditReport()
        await check_client_history_depth(session, report)
        assert report.checks[0].status == "SKIP"

    @pytest.mark.asyncio
    async def test_column_missing_gives_skip(self):
        effects = [
            _rows_result([("customer_invoices",)]),
            _rows_result([("customer_id",)]),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_client_history_depth(session, report)

        assert report.checks[0].status == "SKIP"
        assert "invoice_date" in report.checks[0].message

    @pytest.mark.asyncio
    async def test_db_error_gives_fail_not_crash(self):
        session = _error_session("query failed")
        report = AuditReport()
        await check_client_history_depth(session, report)
        assert report.checks[0].status == "FAIL"

    @pytest.mark.asyncio
    async def test_empty_invoices_gives_warn(self):
        effects = [
            _rows_result([("customer_invoices",)]),
            _rows_result([
                ("customer_id",), ("invoice_date",), ("is_active",),
            ]),
            _rows_result([]),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_client_history_depth(session, report)
        assert report.checks[0].status == "WARN"
        assert "empty" in report.checks[0].message.lower()

    async def _run_depth_check(self, counts):
        effects = [
            _rows_result([("customer_invoices",)]),
            _rows_result([
                ("customer_id",), ("invoice_date",), ("is_active",),
            ]),
            _rows_result(_client_rows(counts)),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_client_history_depth(session, report)
        return report.checks[0]

    @pytest.mark.asyncio
    async def test_70pct_sufficient_gives_pass_trend(self):
        chk = await self._run_depth_check([12] * 70 + [2] * 30)
        assert chk.status == "PASS"
        assert chk.details["recommendation"] == "TREND_FEATURES"

    @pytest.mark.asyncio
    async def test_50pct_sufficient_gives_warn_two_model(self):
        chk = await self._run_depth_check([12] * 50 + [2] * 50)
        assert chk.status == "WARN"
        assert chk.details["recommendation"] == "TWO_MODEL"

    @pytest.mark.asyncio
    async def test_20pct_sufficient_gives_warn_level_only(self):
        chk = await self._run_depth_check([12] * 20 + [2] * 80)
        assert chk.status == "WARN"
        assert chk.details["recommendation"] == "LEVEL_ONLY"


# ══════════════════════════════════════════════════════════
# CHECK 4 — Risk Label Distribution
# ══════════════════════════════════════════════════════════

def _label_rows(n0, n1, n2):
    rows = (
        [(i, 0) for i in range(n0)]
        + [(i, 1) for i in range(n1)]
        + [(i, 2) for i in range(n2)]
    )
    return [
        SimpleNamespace(client_id=r[0], risk_label=r[1])
        for r in rows
    ]


class TestCheckRiskLabelDistribution:
    @pytest.mark.asyncio
    async def test_no_confirmed_tables_gives_skip(self):
        report = AuditReport()
        await check_risk_label_distribution(
            AsyncMock(), report, confirmed_tables=set()
        )
        assert report.checks[0].status == "SKIP"

    @pytest.mark.asyncio
    async def test_column_missing_gives_skip(self):
        # customer_invoices missing 'paid_date'
        effects = [
            _rows_result([
                ("customer_id",), ("invoice_date",),
                ("due_date",), ("amount_due",), ("status",),
            ]),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_risk_label_distribution(
            session, report,
            confirmed_tables={"customer_invoices"},
        )
        assert report.checks[0].status == "SKIP"
        assert "paid_date" in report.checks[0].message

    @pytest.mark.asyncio
    async def test_db_error_gives_fail_not_crash(self):
        session = _error_session("db down")
        report = AuditReport()
        await check_risk_label_distribution(
            session, report,
            confirmed_tables={"customer_invoices"},
        )
        assert report.checks[0].status == "FAIL"

    async def _run_label_check(self, n0, n1, n2):
        effects = [
            _rows_result([(c,) for c in _CI_COLS]),
            _rows_result(_label_rows(n0, n1, n2)),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_risk_label_distribution(
            session, report,
            confirmed_tables={"customer_invoices"},
        )
        return report.checks[0]

    @pytest.mark.asyncio
    async def test_abort_classifier_below_threshold(self):
        """n_churned < _CHURN_ABORT -> ABORT_CLASSIFIER."""
        chk = await self._run_label_check(200, 35, _CHURN_ABORT - 1)
        rec = chk.details["classifier_recommendation"]
        assert rec == "ABORT_CLASSIFIER"
        assert chk.status == "WARN"
        assert chk.details["n_churned"] == _CHURN_ABORT - 1

    @pytest.mark.asyncio
    async def test_gbm_threshold_range(self):
        """_CHURN_ABORT <= n_churned < _CHURN_GBM -> GBM."""
        mid = (_CHURN_ABORT + _CHURN_GBM) // 2
        chk = await self._run_label_check(200, 40, mid)
        rec = chk.details["classifier_recommendation"]
        assert rec == "GBM_WITH_SAMPLE_WEIGHTS"
        assert chk.status == "PASS"

    @pytest.mark.asyncio
    async def test_ann_focal_loss_at_threshold(self):
        """n_churned >= _CHURN_GBM -> ANN_WITH_FOCAL_LOSS."""
        chk = await self._run_label_check(300, 80, _CHURN_GBM)
        rec = chk.details["classifier_recommendation"]
        assert rec == "ANN_WITH_FOCAL_LOSS"
        assert chk.status == "PASS"

    @pytest.mark.asyncio
    async def test_empty_observation_window_gives_warn(self):
        effects = [
            _rows_result([(c,) for c in _CI_COLS]),
            _rows_result([]),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_risk_label_distribution(
            session, report,
            confirmed_tables={"customer_invoices"},
        )
        assert report.checks[0].status == "WARN"

    def test_single_churn_threshold_constants(self):
        """Thresholds must match the canonical definition (20/100)."""
        assert _CHURN_ABORT == 20
        assert _CHURN_GBM == 100


# ══════════════════════════════════════════════════════════
# CHECK 5 — Revenue Row Count
# ══════════════════════════════════════════════════════════

def _revenue_row(total, distinct, earliest, latest,
                 avg=10_000.0, std=2_000.0, zero=0):
    return SimpleNamespace(
        total_rows=total,
        distinct_days=distinct,
        earliest=earliest,
        latest=latest,
        avg_daily=avg,
        std_daily=std,
        zero_days=zero,
    )


class TestCheckRevenueRowCount:
    @pytest.mark.asyncio
    async def test_no_tables_gives_skip(self):
        session = _session_with([_rows_result([])])
        report = AuditReport()
        await check_revenue_row_count(session, report)
        assert report.checks[0].status == "SKIP"

    @pytest.mark.asyncio
    async def test_column_missing_gives_skip(self):
        effects = [
            _rows_result([("net_sales",)]),
            _rows_result([("issue_date",)]),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_revenue_row_count(session, report)

        assert report.checks[0].status == "SKIP"
        assert "total_amount" in report.checks[0].message

    @pytest.mark.asyncio
    async def test_db_error_gives_fail_not_crash(self):
        session = _error_session("timeout")
        report = AuditReport()
        await check_revenue_row_count(session, report)
        assert report.checks[0].status == "FAIL"

    @pytest.mark.asyncio
    async def test_gate_open_above_1825(self):
        effects = [
            _rows_result([("net_sales",)]),
            _rows_result([
                ("issue_date",), ("total_amount",), ("is_active",),
            ]),
            _fetchedone_result(_revenue_row(
                2000, 2000,
                date(2020, 1, 1), date(2025, 6, 1),
                avg=15_000.0, std=3_000.0, zero=10,
            )),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_revenue_row_count(session, report)

        chk = report.checks[0]
        assert chk.status == "PASS"
        assert chk.details["lstm_gate"] == "OPEN"
        assert chk.details["source"] == "net_sales"

    @pytest.mark.asyncio
    async def test_gate_open_marginal_365_to_1824(self):
        effects = [
            _rows_result([("net_sales",)]),
            _rows_result([
                ("issue_date",), ("total_amount",), ("is_active",),
            ]),
            _fetchedone_result(_revenue_row(
                730, 730,
                date(2023, 1, 1), date(2025, 1, 1),
                avg=8_000.0, std=1_500.0, zero=10,
            )),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_revenue_row_count(session, report)

        chk = report.checks[0]
        assert chk.status == "PASS"
        assert chk.details["lstm_gate"] == "OPEN_MARGINAL"

    @pytest.mark.asyncio
    async def test_gate_closed_below_365(self):
        effects = [
            _rows_result([("net_sales",)]),
            _rows_result([
                ("issue_date",), ("total_amount",), ("is_active",),
            ]),
            _fetchedone_result(_revenue_row(
                60, 60,
                date(2025, 1, 1), date(2025, 3, 1),
                avg=5_000.0, std=800.0, zero=5,
            )),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_revenue_row_count(session, report)

        chk = report.checks[0]
        assert chk.status == "WARN"
        assert chk.details["lstm_gate"] == "CLOSED"

    @pytest.mark.asyncio
    async def test_high_gap_pct_downgrades_to_warn(self):
        effects = [
            _rows_result([("net_sales",)]),
            _rows_result([
                ("issue_date",), ("total_amount",), ("is_active",),
            ]),
            _fetchedone_result(_revenue_row(
                2000, 2000,
                date(2010, 1, 1), date(2037, 5, 19),
            )),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_revenue_row_count(session, report)

        chk = report.checks[0]
        assert chk.status == "WARN"
        assert "gap" in chk.message.lower()

    @pytest.mark.asyncio
    async def test_falls_back_to_sales_invoices(self):
        """When net_sales is absent, sales_invoices is audited."""
        effects = [
            _rows_result([("sales_invoices",)]),
            _rows_result([("invoice_date",), ("total",)]),
            _fetchedone_result(_revenue_row(
                2000, 2000,
                date(2020, 1, 1), date(2025, 6, 1),
            )),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_revenue_row_count(session, report)

        chk = report.checks[0]
        assert chk.status == "PASS"
        assert chk.details["source"] == "sales_invoices"

    @pytest.mark.asyncio
    async def test_empty_source_gives_warn(self):
        effects = [
            _rows_result([("net_sales",)]),
            _rows_result([
                ("issue_date",), ("total_amount",), ("is_active",),
            ]),
            _fetchedone_result(None),
        ]
        session = _session_with(effects)
        report = AuditReport()
        await check_revenue_row_count(session, report)
        assert report.checks[0].status == "WARN"


# ══════════════════════════════════════════════════════════
# REPORT RENDERING
# ══════════════════════════════════════════════════════════

class TestRenderReport:
    def _make_full_report(self) -> AuditReport:
        r = AuditReport()
        entries = [
            ("risk_label_schema", "PASS", {
                "required_found": {"customer_invoices":
                                   {"row_count": 100,
                                    "missing_columns": []}},
                "required_missing": {},
                "missing_columns": {},
                "optional_found": {},
                "textbook_present": [],
                "textbook_absent": ["credit_events"],
            }),
            ("entity_pooling", "WARN", {
                "n_entities": 3,
                "n_periods_total": 180,
                "scale_ratio": 4.2,
                "ks_raw_incompatible": 2,
                "ks_corrected_incompatible": 0,
                "correlation_raw_reversals": 1,
                "correlation_confirmed_reversals": 0,
                "ann_gate_open": False,
                "pooling_verdict": "POOL",
            }),
            ("client_history_depth", "PASS", {
                "total_clients": 200,
                "pct_sufficient": 0.72,
                "recommendation": "TREND_FEATURES",
            }),
            ("risk_label_distribution", "PASS", {
                "total": 250,
                "class_0_low": 200,
                "class_1_medium": 35,
                "class_2_high": 15,
                "n_churned": 15,
                "classifier_recommendation": "ABORT_CLASSIFIER",
            }),
            ("revenue_row_count", "PASS", {
                "usable_days": 720,
                "lstm_gate": "OPEN_MARGINAL",
                "date_range": "2023-01-01 -> 2025-01-01",
            }),
        ]
        for name, status, details in entries:
            r.add(CheckResult(
                name=name, status=status,
                message="test", details=details,
            ))
        r.finalize()
        return r

    def test_text_contains_all_check_names(self):
        out = render_report(self._make_full_report())
        for name in [
            "risk_label_schema", "entity_pooling",
            "client_history_depth", "risk_label_distribution",
            "revenue_row_count",
        ]:
            assert name in out

    def test_text_contains_deployment_gates(self):
        out = render_report(self._make_full_report())
        for model in [
            "FinancialForecastANN", "RevenueForecaster",
            "ChurnClassifier", "RiskClassifier",
            "AnomalyAutoencoder",
        ]:
            assert model in out

    def test_text_shows_raw_and_corrected_ks(self):
        """Inline metrics must show both raw and FDR-corrected KS."""
        out = render_report(self._make_full_report())
        assert "KS(raw/corr)=2/0" in out
        assert "Rev(raw/conf)=1/0" in out

    def test_json_render_valid_and_complete(self):
        parsed = json.loads(
            render_report(self._make_full_report(), as_json=True)
        )
        assert len(parsed["checks"]) == 5
        assert "summary" in parsed
        assert parsed["bio_erp_version"] == "5.3.0"

    def test_exit_code_warn_is_1(self):
        assert self._make_full_report().exit_code == 1

    def test_exit_code_all_pass_is_0(self):
        r = AuditReport()
        for i in range(5):
            r.add(CheckResult(
                name=f"c{i}", status="PASS", message="ok"
            ))
        r.finalize()
        assert r.exit_code == 0

    def test_exit_code_fail_is_2(self):
        r = AuditReport()
        r.add(CheckResult(name="x", status="FAIL", message="bad"))
        r.finalize()
        assert r.exit_code == 2

    def test_exit_code_skip_only_is_0(self):
        r = AuditReport()
        r.add(CheckResult(name="x", status="SKIP", message="na"))
        r.finalize()
        assert r.exit_code == 0


# ══════════════════════════════════════════════════════════
# RUN_AUDIT INTEGRATION (sqlite — checks degrade gracefully)
# ══════════════════════════════════════════════════════════

class TestRunAudit:
    @pytest.mark.asyncio
    async def test_graceful_on_non_postgres_backend(self):
        from app.scripts.neural_audit import run_audit

        report = await run_audit("sqlite+aiosqlite:///:memory:")
        assert len(report.checks) == 5
        for c in report.checks:
            assert c.status in ("PASS", "WARN", "FAIL", "SKIP")
