"""
neural_audit.py — BIO-ERP Neural AI Subsystem Runtime Audit
============================================================
Checks the live PostgreSQL database against every assumption the
Neural AI subsystem's circular-label fixes depend on, before any
model is trained on real data.

CHURN-N DEPLOYMENT THRESHOLD (single canonical definition — do not
duplicate elsewhere; see docs/neural_audit.md):
    n_churned < 20   -> ABORT_CLASSIFIER        (rule-based SQL only)
    n_churned 20-99  -> GBM_WITH_SAMPLE_WEIGHTS
    n_churned >= 100 -> ANN_WITH_FOCAL_LOSS

where n_churned is the number of clients labelled high-risk (class 2)
in the observation window. SMOTE is prohibited on financial
time-series data (synthetic interpolation violates temporal ordering).

SCHEMA-FIRST POLICY:
    Every check that queries a table MUST first confirm that table
    and its required columns exist via information_schema. A missing
    table or column produces a SKIP or WARN result — never a crash,
    never a silent assumption. Column names below reflect the REAL
    BIO-ERP schema (customer_id / amount_due / status / paid_date on
    customer_invoices; net_sales and sales_invoices for revenue), not
    textbook names.

ENTITY-POOLING STATISTICAL CORRECTIONS:
    - Benjamini-Hochberg FDR correction across all pairwise KS tests
      before any pair is flagged incompatible (raw counts also shown).
    - Correlation reversals require two entities whose 90% bootstrap
      CIs (1,000 resamples) do not overlap in sign. A single
      point-estimate sign flip at N=24-60 is sampling noise, not
      Simpson's Paradox. Only confirmed reversals drive DO_NOT_POOL.

Exit codes (for CI/CD):
    0 — all checks PASS or SKIP
    1 — at least one WARN, no FAIL
    2 — at least one FAIL or unhandled error

Usage:
    python -m app.scripts.neural_audit
    python -m app.scripts.neural_audit --json
    python -m app.scripts.neural_audit --out reports/audit.json
    python -m app.scripts.neural_audit --db-url postgresql+asyncpg://...
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import textwrap
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ── Optional dependency guards ────────────────────────────
try:
    import numpy as np
    _NUMPY = True
except ImportError:
    _NUMPY = False

try:
    from scipy.stats import ks_2samp
    _SCIPY = True
except ImportError:
    _SCIPY = False

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    _SQLA = True
except ImportError:
    _SQLA = False


# ══════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════

@dataclass
class CheckResult:
    name: str
    status: str  # PASS | WARN | FAIL | SKIP
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    action: str = ""


@dataclass
class AuditReport:
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    bio_erp_version: str = "5.3.0"
    checks: list[CheckResult] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)

    def finalize(self) -> AuditReport:
        counts: dict[str, int] = {
            "PASS": 0, "WARN": 0, "FAIL": 0, "SKIP": 0
        }
        for c in self.checks:
            counts[c.status] = counts.get(c.status, 0) + 1
        self.summary = counts
        return self

    @property
    def exit_code(self) -> int:
        if self.summary.get("FAIL", 0) > 0:
            return 2
        if self.summary.get("WARN", 0) > 0:
            return 1
        return 0


# ══════════════════════════════════════════════════════════
# SCHEMA HELPERS (schema-first policy — used by every check)
# ══════════════════════════════════════════════════════════

async def _existing_tables(session: AsyncSession) -> set[str]:
    """Return set of BASE TABLE names in the public schema."""
    r = await session.execute(text(
        "SELECT table_name "
        "FROM information_schema.tables "
        "WHERE table_schema = 'public' "
        "  AND table_type   = 'BASE TABLE'"
    ))
    return {row[0] for row in r.fetchall()}


async def _existing_columns(session: AsyncSession, table: str) -> set[str]:
    """Return set of column names for *table* in the public schema."""
    r = await session.execute(
        text(
            "SELECT column_name "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "  AND table_name   = :tbl"
        ),
        {"tbl": table},
    )
    return {row[0] for row in r.fetchall()}


async def _row_count(session: AsyncSession, table: str) -> int:
    """Return COUNT(*) for *table* (name comes from our own lists)."""
    r = await session.execute(
        text(f"SELECT COUNT(*) FROM {table}")
    )
    return int(r.scalar() or 0)


# ══════════════════════════════════════════════════════════
# STATISTICAL HELPERS (entity-pooling check)
# ══════════════════════════════════════════════════════════

def _benjamini_hochberg(
    p_values: list[float],
    alpha: float = 0.05,
) -> list[bool]:
    """
    Benjamini-Hochberg FDR correction (step-up).
    Returns a boolean mask aligned with the input order:
    True = reject H0 after correction.
    """
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    max_passing_rank = 0
    for rank, idx in enumerate(order, start=1):
        if p_values[idx] <= (rank / m) * alpha:
            max_passing_rank = rank
    reject = [False] * m
    for rank, idx in enumerate(order, start=1):
        if rank <= max_passing_rank:
            reject[idx] = True
    return reject


def _bootstrap_correlation_ci(
    x: np.ndarray,
    y: np.ndarray,
    n_boot: int = 1_000,
    ci: float = 0.90,
    rng_seed: int = 42,
) -> tuple[float, float, float]:
    """
    Bootstrap confidence interval for Pearson correlation.
    Returns (point_estimate, ci_lower, ci_upper).
    Falls back to (nan, nan, nan) if arrays are too short.
    """
    if not _NUMPY:
        return float("nan"), float("nan"), float("nan")
    n = len(x)
    if n < 4:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(rng_seed)
    point = float(np.corrcoef(x, y)[0, 1])
    boot_corrs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        xb, yb = x[idx], y[idx]
        if np.std(xb) > 0 and np.std(yb) > 0:
            boot_corrs.append(float(np.corrcoef(xb, yb)[0, 1]))
    if not boot_corrs:
        return point, float("nan"), float("nan")
    lo = float(np.percentile(boot_corrs, 100 * (1 - ci) / 2))
    hi = float(np.percentile(boot_corrs, 100 * (1 - (1 - ci) / 2)))
    return point, lo, hi


# ══════════════════════════════════════════════════════════
# CHECK 1 — Risk Label Schema
# ══════════════════════════════════════════════════════════

# Columns the downstream checks need per table. These reflect the
# REAL BIO-ERP schema (verified against app/models), not textbook
# names: customer_invoices uses customer_id/amount_due/status/
# paid_date; written-off invoices are status='WRITTEN_OFF'.
_REQUIRED_COLUMNS: dict[str, list[str]] = {
    "customer_invoices": [
        "customer_id", "invoice_date", "due_date",
        "amount_due", "status", "paid_date",
    ],
    "ar_customers": ["id", "status"],
    "net_sales": [
        "client_id", "issue_date", "total_amount", "is_active",
    ],
    "sales_invoices": ["invoice_date", "total"],
    "purchase_orders": ["vendor_id", "po_date", "status"],
}

_OPTIONAL_TABLES: dict[str, str] = {
    "budget_variances": "Budgeting — variance records",
    "journal_entries": "GL — journal entries",
    "financial_periods": "Entity-level period aggregations",
}

# Textbook tables that must NOT be assumed to exist. If present they
# are reported; risk-label SQL never depends on them.
_TEXTBOOK_TABLES: list[str] = [
    "credit_events",
    "covenant_breaches",
    "audit_qualifications",
    "credit_ratings",
]


async def check_risk_label_schema(
    session: AsyncSession,
    report: AuditReport,
) -> set[str]:
    """
    Introspect information_schema for required tables AND their
    required columns. Returns the set of required tables actually
    found (consumed by Check 4).
    """
    print("[1/5] Verifying risk label schema ...")
    found_required: dict[str, dict] = {}
    missing_required: dict[str, str] = {}
    missing_columns: dict[str, list[str]] = {}
    optional_found: dict[str, int] = {}
    textbook_present: list[str] = []

    try:
        existing = await _existing_tables(session)

        for tbl, req_cols in _REQUIRED_COLUMNS.items():
            if tbl not in existing:
                missing_required[tbl] = (
                    "Table not found in public schema"
                )
                continue
            actual_cols = await _existing_columns(session, tbl)
            absent = [c for c in req_cols if c not in actual_cols]
            if absent:
                missing_columns[tbl] = absent
            row_ct = await _row_count(session, tbl)
            found_required[tbl] = {
                "row_count": row_ct,
                "missing_columns": absent,
            }

        for tbl in _OPTIONAL_TABLES:
            if tbl in existing:
                optional_found[tbl] = await _row_count(session, tbl)

        textbook_present = [
            t for t in _TEXTBOOK_TABLES if t in existing
        ]

        col_failures = {
            t: cols for t, cols in missing_columns.items() if cols
        }
        if missing_required:
            status = "FAIL"
            message = (
                f"{len(missing_required)} required table(s) missing: "
                f"{list(missing_required.keys())}"
            )
            action = (
                "Create missing tables or adjust risk-label SQL "
                "to use only confirmed tables."
            )
        elif col_failures:
            status = "WARN"
            message = (
                f"All {len(_REQUIRED_COLUMNS)} tables present but "
                f"{len(col_failures)} have missing columns: "
                f"{col_failures}"
            )
            action = (
                "Add missing columns or update downstream queries "
                "to avoid them."
            )
        else:
            status = "PASS"
            message = (
                f"All {len(_REQUIRED_COLUMNS)} required tables "
                f"present with required columns. "
                f"{len(_TEXTBOOK_TABLES) - len(textbook_present)} "
                f"textbook tables correctly absent."
            )
            action = ""

        report.add(CheckResult(
            name="risk_label_schema",
            status=status,
            message=message,
            action=action,
            details={
                "required_found": found_required,
                "required_missing": missing_required,
                "missing_columns": missing_columns,
                "optional_found": optional_found,
                "textbook_present": textbook_present,
                "textbook_absent": [
                    t for t in _TEXTBOOK_TABLES
                    if t not in textbook_present
                ],
            },
        ))
        return set(found_required.keys())

    except Exception as exc:
        report.add(CheckResult(
            name="risk_label_schema",
            status="FAIL",
            message=f"Schema introspection failed: {exc}",
            action="Check DB connection and credentials.",
        ))
        return set()


# ══════════════════════════════════════════════════════════
# CHECK 2 — Entity Pooling Validity
# ══════════════════════════════════════════════════════════

async def check_entity_pooling_validity(
    session: AsyncSession,
    report: AuditReport,
) -> None:
    """
    Tests whether GL entities are exchangeable enough to pool for
    FinancialForecastANN training.

    Statistical rigour (per design-review corrections):
    - KS tests with Benjamini-Hochberg FDR correction across all
      pairwise comparisons before flagging any pair incompatible.
    - Correlation sign via 1,000-resample bootstrap CI; a reversal
      is confirmed only when two entities' CIs do not overlap in
      sign. Both raw and corrected counts are reported.
    """
    print("[2/5] Checking entity pooling validity ...")

    if not _SCIPY or not _NUMPY:
        report.add(CheckResult(
            name="entity_pooling",
            status="SKIP",
            message="scipy / numpy not available.",
            action="conda install -c conda-forge scipy numpy",
        ))
        return

    try:
        existing = await _existing_tables(session)
    except Exception as exc:
        report.add(CheckResult(
            name="entity_pooling",
            status="FAIL",
            message=f"Schema query failed: {exc}",
            action="Check DB connection.",
        ))
        return

    if "financial_periods" not in existing:
        report.add(CheckResult(
            name="entity_pooling",
            status="SKIP",
            message=(
                "financial_periods table not found. "
                "Cannot assess pooling validity."
            ),
            action=(
                "Create financial_periods view/table or re-run "
                "after GL data is loaded."
            ),
        ))
        return

    needed_cols = {
        "entity_id", "period_date",
        "total_revenue", "revenue_growth", "eva_next_period",
    }
    try:
        actual_cols = await _existing_columns(
            session, "financial_periods"
        )
    except Exception as exc:
        report.add(CheckResult(
            name="entity_pooling",
            status="FAIL",
            message=f"Schema query failed: {exc}",
            action="Check DB connection.",
        ))
        return
    absent_cols = needed_cols - actual_cols
    if absent_cols:
        report.add(CheckResult(
            name="entity_pooling",
            status="SKIP",
            message=(
                f"financial_periods missing columns: "
                f"{sorted(absent_cols)}. Cannot run pooling check."
            ),
            action="Add missing columns to financial_periods.",
        ))
        return

    try:
        r = await session.execute(text("""
            SELECT
                entity_id,
                COUNT(*)           AS n_periods,
                AVG(total_revenue) AS avg_revenue
            FROM financial_periods
            GROUP BY entity_id
            HAVING COUNT(*) >= 6
        """))
        entity_rows = r.fetchall()

        if len(entity_rows) < 2:
            report.add(CheckResult(
                name="entity_pooling",
                status="WARN",
                message=(
                    f"Only {len(entity_rows)} entity/entities with "
                    f">=6 periods. Pooling not applicable."
                ),
                action=(
                    "Use single-entity Ridge/GBM. "
                    "ANN gate stays CLOSED."
                ),
                details={"entities_with_sufficient_data":
                         len(entity_rows)},
            ))
            return

        entity_ids = [row.entity_id for row in entity_rows]

        revenues = [float(row.avg_revenue or 0) for row in entity_rows]
        max_rev = max(revenues)
        positives = [v for v in revenues if v > 0]
        min_rev = min(positives) if positives else 1.0
        scale_ratio = max_rev / min_rev

        # ── Load revenue series per entity ────────────────
        entity_series: dict[Any, np.ndarray] = {}
        for eid in entity_ids:
            rs = await session.execute(
                text(
                    "SELECT total_revenue "
                    "FROM financial_periods "
                    "WHERE entity_id = :eid "
                    "ORDER BY period_date"
                ),
                {"eid": eid},
            )
            vals = [float(row[0] or 0) for row in rs.fetchall()]
            if vals:
                entity_series[eid] = np.array(vals)

        # ── Pairwise KS tests (FDR-corrected) ─────────────
        pairs: list[tuple[Any, Any]] = []
        raw_ps: list[float] = []
        eids = list(entity_series.keys())
        for i in range(len(eids)):
            for j in range(i + 1, len(eids)):
                a, b = eids[i], eids[j]
                if (len(entity_series[a]) >= 4
                        and len(entity_series[b]) >= 4):
                    _, p = ks_2samp(entity_series[a], entity_series[b])
                    pairs.append((a, b))
                    raw_ps.append(p)

        reject_mask = _benjamini_hochberg(raw_ps)
        raw_incompatible = sum(1 for p in raw_ps if p < 0.05)
        corrected_incompatible = sum(reject_mask)

        # ── Bootstrap correlation signs ───────────────────
        entity_corr: dict[Any, tuple[float, float, float]] = {}
        for eid in eids:
            rc = await session.execute(
                text(
                    "SELECT revenue_growth, eva_next_period "
                    "FROM financial_periods "
                    "WHERE entity_id = :eid "
                    "  AND revenue_growth IS NOT NULL "
                    "  AND eva_next_period IS NOT NULL "
                    "ORDER BY period_date"
                ),
                {"eid": eid},
            )
            rows = rc.fetchall()
            if len(rows) >= 4:
                x = np.array([float(row[0]) for row in rows])
                y = np.array([float(row[1]) for row in rows])
                entity_corr[eid] = _bootstrap_correlation_ci(x, y)

        raw_reversals = 0
        confirmed_reversals = 0
        reversal_pairs: list[dict] = []
        corr_eids = list(entity_corr.keys())
        for i in range(len(corr_eids)):
            for j in range(i + 1, len(corr_eids)):
                ea, eb = corr_eids[i], corr_eids[j]
                pa, la, ha = entity_corr[ea]
                pb, lb, hb = entity_corr[eb]

                if (not (np.isnan(pa) or np.isnan(pb))
                        and np.sign(pa) != np.sign(pb)):
                    raw_reversals += 1

                ci_a_pos = la > 0 and ha > 0
                ci_a_neg = la < 0 and ha < 0
                ci_b_pos = lb > 0 and hb > 0
                ci_b_neg = lb < 0 and hb < 0
                if (ci_a_pos and ci_b_neg) or (ci_a_neg and ci_b_pos):
                    confirmed_reversals += 1
                    reversal_pairs.append({
                        "entity_a": ea,
                        "entity_b": eb,
                        "corr_a": round(pa, 3),
                        "ci_a": [round(la, 3), round(ha, 3)],
                        "corr_b": round(pb, 3),
                        "ci_b": [round(lb, 3), round(hb, 3)],
                    })

        n_periods_total = sum(int(row.n_periods) for row in entity_rows)

        pooling_valid = (
            corrected_incompatible == 0
            and confirmed_reversals == 0
            and scale_ratio <= 100
        )

        if pooling_valid:
            gate = (
                "OPEN"
                if n_periods_total >= 500
                else "CLOSED — pooled N=" + str(n_periods_total)
                     + " < 500"
            )
            status = "PASS"
            message = (
                f"{len(entity_ids)} entities pass pooling checks. "
                f"Pooled N={n_periods_total}. "
                f"Scale={scale_ratio:.1f}x. "
                f"KS incompatible (corrected)={corrected_incompatible}. "
                f"Confirmed reversals={confirmed_reversals}. "
                f"ANN gate: {gate}."
            )
            action = ""
        else:
            reasons = []
            if corrected_incompatible > 0:
                reasons.append(
                    f"{corrected_incompatible} FDR-corrected KS "
                    f"incompatibilities"
                )
            if confirmed_reversals > 0:
                reasons.append(
                    f"{confirmed_reversals} bootstrap-confirmed "
                    f"correlation reversals"
                )
            if scale_ratio > 100:
                reasons.append(f"scale ratio {scale_ratio:.0f}x > 100x")
            status = "WARN"
            message = (
                f"DO_NOT_POOL: {'; '.join(reasons)}. "
                f"Raw KS failures={raw_incompatible} "
                f"(before FDR correction). "
                f"Raw sign reversals={raw_reversals} "
                f"(before bootstrap CI check)."
            )
            action = (
                "Use separate Ridge/GBM per entity, or hierarchical "
                "mixed-effects model. ANN gate stays CLOSED."
            )

        report.add(CheckResult(
            name="entity_pooling",
            status=status,
            message=message,
            action=action,
            details={
                "n_entities": len(entity_ids),
                "n_periods_total": n_periods_total,
                "scale_ratio": round(scale_ratio, 2),
                "ks_raw_incompatible": raw_incompatible,
                "ks_corrected_incompatible": corrected_incompatible,
                "correlation_raw_reversals": raw_reversals,
                "correlation_confirmed_reversals": confirmed_reversals,
                "reversal_pairs": reversal_pairs,
                "ann_gate_open": (
                    pooling_valid and n_periods_total >= 500
                ),
                "pooling_verdict": (
                    "POOL" if pooling_valid else "DO_NOT_POOL"
                ),
            },
        ))

    except Exception as exc:
        report.add(CheckResult(
            name="entity_pooling",
            status="FAIL",
            message=f"Pooling check failed: {exc}",
            action="Check financial_periods table and DB.",
        ))


# ══════════════════════════════════════════════════════════
# CHECK 3 — Client History Depth
# ══════════════════════════════════════════════════════════

async def check_client_history_depth(
    session: AsyncSession,
    report: AuditReport,
    min_periods: int = 6,
) -> None:
    """
    % of clients with >= min_periods monthly observations.
    Thresholds (not disputed in review):
        >= 70%   -> TREND_FEATURES
        40-69%   -> TWO_MODEL
        < 40%    -> LEVEL_ONLY
    """
    print("[3/5] Checking client history depth ...")

    try:
        existing = await _existing_tables(session)
    except Exception as exc:
        report.add(CheckResult(
            name="client_history_depth",
            status="FAIL",
            message=f"Schema query failed: {exc}",
            action="Check DB connection.",
        ))
        return

    if "customer_invoices" not in existing:
        report.add(CheckResult(
            name="client_history_depth",
            status="SKIP",
            message="customer_invoices table not found.",
            action="Check schema — table required for churn.",
        ))
        return

    try:
        cols = await _existing_columns(session, "customer_invoices")
    except Exception as exc:
        report.add(CheckResult(
            name="client_history_depth",
            status="FAIL",
            message=f"Schema query failed: {exc}",
            action="Check DB connection.",
        ))
        return
    needed = {"customer_id", "invoice_date", "is_active"}
    absent = needed - cols
    if absent:
        report.add(CheckResult(
            name="client_history_depth",
            status="SKIP",
            message=(
                f"customer_invoices missing columns: {sorted(absent)}"
            ),
            action="Add missing columns.",
        ))
        return

    try:
        r = await session.execute(text("""
            SELECT
                customer_id                                        AS client_id,
                COUNT(DISTINCT DATE_TRUNC('month', invoice_date))  AS n_months,
                COUNT(*)                                           AS total_invoices,
                MIN(invoice_date)                                  AS first_invoice,
                MAX(invoice_date)                                  AS last_invoice
            FROM customer_invoices
            WHERE is_active = TRUE
            GROUP BY customer_id
        """))
        clients = r.fetchall()

        if not clients:
            report.add(CheckResult(
                name="client_history_depth",
                status="WARN",
                message="customer_invoices is empty.",
                action="Load invoice data before training.",
            ))
            return

        n_total = len(clients)
        counts = [int(c.n_months) for c in clients]
        n_sufficient = sum(1 for c in counts if c >= min_periods)
        pct = n_sufficient / n_total

        if _NUMPY:
            median_m = float(np.median(counts))
        else:
            sorted_c = sorted(counts)
            mid = n_total // 2
            median_m = (
                float(sorted_c[mid])
                if n_total % 2
                else (sorted_c[mid - 1] + sorted_c[mid]) / 2.0
            )

        buckets = {
            "0-2": sum(1 for c in counts if c <= 2),
            "3-5": sum(1 for c in counts if 3 <= c <= 5),
            "6-11": sum(1 for c in counts if 6 <= c <= 11),
            "12-23": sum(1 for c in counts if 12 <= c <= 23),
            "24+": sum(1 for c in counts if c >= 24),
        }

        if pct >= 0.70:
            rec = "TREND_FEATURES"
            status = "PASS"
            action = ""
        elif pct >= 0.40:
            rec = "TWO_MODEL"
            status = "WARN"
            action = (
                f"Use trend features for {n_sufficient} established "
                f"clients; level features + trend_available=0 flag "
                f"for the rest."
            )
        else:
            rec = "LEVEL_ONLY"
            status = "WARN"
            action = (
                "Use level features only. Churn model will miss "
                "trend signal. Prefer GBM over ANN."
            )

        report.add(CheckResult(
            name="client_history_depth",
            status=status,
            message=(
                f"{n_sufficient}/{n_total} clients ({pct:.0%}) have "
                f">={min_periods} months. Recommendation: {rec}."
            ),
            action=action,
            details={
                "total_clients": n_total,
                "sufficient": n_sufficient,
                "pct_sufficient": round(pct, 3),
                "median_months": round(median_m, 1),
                "min_months": min(counts),
                "max_months": max(counts),
                "distribution": buckets,
                "min_required": min_periods,
                "recommendation": rec,
            },
        ))

    except Exception as exc:
        report.add(CheckResult(
            name="client_history_depth",
            status="FAIL",
            message=f"History depth query failed: {exc}",
            action="Check customer_invoices schema.",
        ))


# ══════════════════════════════════════════════════════════
# CHECK 4 — Risk Label Distribution
# ══════════════════════════════════════════════════════════

# CHURN-N THRESHOLD (single canonical definition — see module
# docstring and docs/neural_audit.md; do not redefine elsewhere):
_CHURN_ABORT = 20   # n_churned < 20  -> rule-based only
_CHURN_GBM = 100    # 20-99 -> GBM + sample_weight
                    # >=100 -> ANN + Focal Loss


async def check_risk_label_distribution(
    session: AsyncSession,
    report: AuditReport,
    confirmed_tables: set[str],
    horizon_days: int = 180,
) -> None:
    """
    Build risk labels ONLY from tables confirmed by Check 1.
    Class thresholds: see _CHURN_ABORT / _CHURN_GBM above and the
    module docstring. n_churned = class-2 (high-risk) count.

    Label legs use REAL schema columns:
      high:   status='WRITTEN_OFF'; payment stoppage proxy
              (amount_due > 0, unpaid, >90 days past due)
      medium: paid >60 days late; PO cancellations;
              budget variances < -30% (optional tables)
    """
    print("[4/5] Auditing risk label distribution ...")

    required_for_labels = {"customer_invoices"}
    available = required_for_labels & confirmed_tables
    if not available:
        report.add(CheckResult(
            name="risk_label_distribution",
            status="SKIP",
            message=(
                "customer_invoices was not confirmed by Check 1. "
                "Cannot build labels."
            ),
            action="Fix schema issues found in Check 1 first.",
        ))
        return

    # Column guard — query each confirmed table once, cache results.
    needed_by_table = {
        "customer_invoices": {
            "customer_id", "invoice_date", "due_date",
            "amount_due", "status", "paid_date",
        },
    }
    cols_cache: dict[str, set[str]] = {}
    col_issues: list[str] = []
    try:
        for tbl, needed in needed_by_table.items():
            if tbl not in confirmed_tables:
                continue
            actual = await _existing_columns(session, tbl)
            cols_cache[tbl] = actual
            absent = needed - actual
            if absent:
                col_issues.append(f"{tbl}: missing {sorted(absent)}")
    except Exception as exc:
        report.add(CheckResult(
            name="risk_label_distribution",
            status="FAIL",
            message=f"Column verification failed: {exc}",
            action="Check DB connection.",
        ))
        return

    if col_issues:
        report.add(CheckResult(
            name="risk_label_distribution",
            status="SKIP",
            message=(
                "Required columns absent for label SQL: "
                + "; ".join(col_issues)
            ),
            action="Add missing columns (see Check 1 details).",
        ))
        return

    obs_date = datetime.now() - timedelta(days=horizon_days)
    horizon_date = datetime.now()
    params = {"obs_date": obs_date, "horizon_date": horizon_date}

    # Build label SQL dynamically from confirmed tables only.
    high_legs: list[str] = []
    medium_legs: list[str] = []
    ci_cols = cols_cache["customer_invoices"]

    # High leg 1: written-off invoices
    if "status" in ci_cols:
        high_legs.append("""
            SELECT customer_id AS client_id
            FROM customer_invoices
            WHERE status = 'WRITTEN_OFF'
              AND invoice_date BETWEEN :obs_date AND :horizon_date
        """)

    # High leg 2: payment stoppage proxy (unpaid, >90 days overdue)
    if {"amount_due", "due_date", "paid_date"} <= ci_cols:
        high_legs.append("""
            SELECT customer_id AS client_id
            FROM customer_invoices
            WHERE amount_due > 0
              AND due_date < :obs_date
              AND paid_date IS NULL
              AND (CAST(:horizon_date AS DATE) - due_date) > 90
        """)

    # Medium leg 1: paid more than 60 days late
    if {"due_date", "paid_date"} <= ci_cols:
        medium_legs.append("""
            SELECT customer_id AS client_id
            FROM customer_invoices
            WHERE paid_date IS NOT NULL
              AND due_date IS NOT NULL
              AND paid_date > due_date
              AND (paid_date - due_date) > 60
              AND invoice_date BETWEEN :obs_date AND :horizon_date
        """)

    # Medium leg 2: cancelled POs (supplier default proxy)
    if "purchase_orders" in confirmed_tables:
        po_cols = await _existing_columns(session, "purchase_orders")
        if {"vendor_id", "status", "po_date"} <= po_cols:
            medium_legs.append("""
                SELECT vendor_id AS client_id
                FROM purchase_orders
                WHERE status = 'CANCELLED'
                  AND po_date BETWEEN :obs_date AND :horizon_date
            """)

    # Medium leg 3: budget variances worse than -30%
    if "budget_variances" in confirmed_tables:
        bv_cols = await _existing_columns(session, "budget_variances")
        if {"entity_id", "variance_pct", "period_date"} <= bv_cols:
            medium_legs.append("""
                SELECT entity_id AS client_id
                FROM budget_variances
                WHERE variance_pct < -0.30
                  AND period_date BETWEEN :obs_date AND :horizon_date
            """)

    if not high_legs and not medium_legs:
        report.add(CheckResult(
            name="risk_label_distribution",
            status="SKIP",
            message=(
                "No usable label SQL legs after column verification. "
                "Cannot build risk labels."
            ),
            action="Check column names in confirmed tables.",
        ))
        return

    high_union = (
        " UNION ".join(high_legs)
        or "SELECT NULL::bigint AS client_id WHERE FALSE"
    )
    medium_union = (
        " UNION ".join(medium_legs)
        or "SELECT NULL::bigint AS client_id WHERE FALSE"
    )

    try:
        r = await session.execute(text(f"""
            WITH observation_clients AS (
                SELECT DISTINCT customer_id AS client_id
                FROM customer_invoices
                WHERE invoice_date <= :obs_date
            ),
            high_risk AS (
                SELECT DISTINCT client_id, 2 AS risk_class
                FROM ({high_union}) h
            ),
            medium_risk AS (
                SELECT DISTINCT client_id, 1 AS risk_class
                FROM ({medium_union}) m
                WHERE client_id NOT IN (
                    SELECT client_id FROM high_risk
                )
            )
            SELECT
                oc.client_id                                       AS client_id,
                COALESCE(hr.risk_class, mr.risk_class, 0)          AS risk_label
            FROM observation_clients oc
            LEFT JOIN high_risk   hr USING (client_id)
            LEFT JOIN medium_risk mr USING (client_id)
        """), params)
        rows = r.fetchall()
        total = len(rows)

        if total == 0:
            report.add(CheckResult(
                name="risk_label_distribution",
                status="WARN",
                message=(
                    "No client records in observation window "
                    f"({obs_date.date()} -> {horizon_date.date()})."
                ),
                action="Widen horizon or check invoice data.",
            ))
            return

        dist = Counter(int(row.risk_label) for row in rows)
        n0, n1, n2 = dist[0], dist[1], dist[2]
        minority = min(n1, n2) if min(n1, n2) > 0 else 1
        majority = max(n0, n1, n2)
        imbalance = majority / minority

        # Single canonical threshold (module docstring):
        if n2 < _CHURN_ABORT:
            rec = "ABORT_CLASSIFIER"
            note = (
                f"Only {n2} high-risk examples "
                f"(threshold: {_CHURN_ABORT}). "
                "Use rule-based SQL scoring only."
            )
            status = "WARN"
        elif n2 < _CHURN_GBM:
            rec = "GBM_WITH_SAMPLE_WEIGHTS"
            note = (
                f"{n2} high-risk examples "
                f"({_CHURN_ABORT}-{_CHURN_GBM - 1} range). "
                "GBM with sample_weight. No ANN, no SMOTE."
            )
            status = "PASS"
        else:
            rec = "ANN_WITH_FOCAL_LOSS"
            note = (
                f"{n2} high-risk examples (>= {_CHURN_GBM}). "
                "ANN with Focal Loss viable."
            )
            status = "PASS"

        report.add(CheckResult(
            name="risk_label_distribution",
            status=status,
            message=(
                f"Total={total}. "
                f"Class 0={n0} ({100 * n0 / total:.1f}%), "
                f"Class 1={n1} ({100 * n1 / total:.1f}%), "
                f"Class 2={n2} ({100 * n2 / total:.1f}%). "
                f"Imbalance={imbalance:.1f}x."
            ),
            action=note,
            details={
                "total": total,
                "class_0_low": n0,
                "class_1_medium": n1,
                "class_2_high": n2,
                "n_churned": n2,
                "imbalance_ratio": round(imbalance, 2),
                "observation_date": obs_date.isoformat(),
                "horizon_date": horizon_date.isoformat(),
                "horizon_days": horizon_days,
                "classifier_recommendation": rec,
                "thresholds_used": {
                    "abort_below": _CHURN_ABORT,
                    "gbm_below": _CHURN_GBM,
                    "ann_focal_above": _CHURN_GBM,
                },
                "label_legs_used": {
                    "high_risk": len(high_legs),
                    "medium_risk": len(medium_legs),
                },
            },
        ))

    except Exception as exc:
        report.add(CheckResult(
            name="risk_label_distribution",
            status="FAIL",
            message=f"Label construction failed: {exc}",
            action="Check confirmed tables and columns.",
        ))


# ══════════════════════════════════════════════════════════
# CHECK 5 — Revenue Row Count (LSTM Gate)
# ══════════════════════════════════════════════════════════

# Candidate daily-revenue sources, in priority order. Each entry:
# (table, required columns, date column, amount expression, active filter)
_REVENUE_SOURCES = [
    ("net_sales", {"issue_date", "total_amount", "is_active"},
     "issue_date", "COALESCE(total_amount, 0)", "is_active = TRUE"),
    ("sales_invoices", {"invoice_date", "total"},
     "invoice_date", "COALESCE(total, 0)", "TRUE"),
]


async def check_revenue_row_count(
    session: AsyncSession,
    report: AuditReport,
) -> None:
    """
    Usable daily-revenue rows. LSTM gate:
    OPEN >=1825 days, OPEN_MARGINAL >=365, CLOSED <365.
    Uses net_sales when available, falls back to sales_invoices.
    """
    print("[5/5] Checking revenue data volume for LSTM gate ...")

    try:
        existing = await _existing_tables(session)
    except Exception as exc:
        report.add(CheckResult(
            name="revenue_row_count",
            status="FAIL",
            message=f"Schema query failed: {exc}",
            action="Check DB connection.",
        ))
        return

    source = None
    source_gaps: list[str] = []
    try:
        for tbl, needed, date_col, amount_expr, active_filter in (
            _REVENUE_SOURCES
        ):
            if tbl not in existing:
                source_gaps.append(f"{tbl}: table not found")
                continue
            cols = await _existing_columns(session, tbl)
            absent = needed - cols
            if absent:
                source_gaps.append(f"{tbl}: missing {sorted(absent)}")
                continue
            source = (tbl, date_col, amount_expr, active_filter)
            break
    except Exception as exc:
        report.add(CheckResult(
            name="revenue_row_count",
            status="FAIL",
            message=f"Schema query failed: {exc}",
            action="Check DB connection.",
        ))
        return

    if source is None:
        report.add(CheckResult(
            name="revenue_row_count",
            status="SKIP",
            message=(
                "No usable revenue source. " + "; ".join(source_gaps)
            ),
            action="Create net_sales or use sales_invoices with date "
                   "and amount columns.",
        ))
        return

    tbl, date_col, amount_expr, active_filter = source

    try:
        r = await session.execute(text(f"""
            SELECT
                COUNT(*)                                AS total_rows,
                COUNT(DISTINCT DATE_TRUNC('day', {date_col}))
                                                        AS distinct_days,
                MIN({date_col})                         AS earliest,
                MAX({date_col})                         AS latest,
                AVG(daily_revenue)                      AS avg_daily,
                STDDEV(daily_revenue)                   AS std_daily,
                SUM(CASE WHEN daily_revenue IS NULL
                          OR daily_revenue = 0
                    THEN 1 ELSE 0 END)                  AS zero_days
            FROM (
                SELECT
                    DATE_TRUNC('day', {date_col}) AS day,
                    SUM({amount_expr})            AS daily_revenue
                FROM {tbl}
                WHERE {date_col} IS NOT NULL
                  AND {active_filter}
                GROUP BY DATE_TRUNC('day', {date_col})
            ) daily
        """))
        row = r.fetchone()

        if not row or not row.total_rows:
            report.add(CheckResult(
                name="revenue_row_count",
                status="WARN",
                message=f"{tbl} is empty.",
                action="Load sales data before training.",
            ))
            return

        total_rows = int(row.total_rows or 0)
        distinct_days = int(row.distinct_days or 0)
        earliest = row.earliest
        latest = row.latest
        avg_daily = float(row.avg_daily or 0)
        std_daily = float(row.std_daily or 0)
        zero_days = int(row.zero_days or 0)
        usable_days = distinct_days - zero_days

        span_days = (
            (latest - earliest).days if earliest and latest else 0
        )
        gap_pct = (
            1 - distinct_days / span_days if span_days > 0 else 0.0
        )

        if usable_days >= 1825:
            gate = "OPEN"
            status = "PASS"
            note = (
                f"{usable_days} usable days (>=1825). "
                "LSTM fully viable. "
                "Use last 90 days as temporal test set."
            )
        elif usable_days >= 365:
            gate = "OPEN_MARGINAL"
            status = "PASS"
            note = (
                f"{usable_days} usable days (>=365, <1825). "
                "LSTM marginal — use hidden_size=32 not 64. "
                "Consider Prophet/ARIMA until N>=1825."
            )
        elif usable_days >= 90:
            gate = "CLOSED"
            status = "WARN"
            note = (
                f"{usable_days} usable days (<365). "
                "LSTM gate CLOSED. Use Prophet or ARIMA."
            )
        else:
            gate = "CLOSED"
            status = "WARN"
            note = (
                f"Only {usable_days} usable days. "
                "Insufficient for time-series model. "
                "Use simple moving average."
            )

        if gap_pct > 0.20:
            status = "WARN"
            note += (
                f" WARNING: {gap_pct:.0%} calendar-day gap — "
                "check for missing data before training."
            )

        report.add(CheckResult(
            name="revenue_row_count",
            status=status,
            message=note,
            action=(
                "" if gate.startswith("OPEN")
                else "Use Prophet/ARIMA instead of LSTM."
            ),
            details={
                "source": tbl,
                "total_rows": total_rows,
                "distinct_days": distinct_days,
                "usable_days": usable_days,
                "zero_days": zero_days,
                "span_days": span_days,
                "gap_pct": round(gap_pct, 3),
                "avg_daily_rev": round(avg_daily, 2),
                "std_daily_rev": round(std_daily, 2),
                "lstm_gate": gate,
                "date_range": (
                    f"{earliest} -> {latest}" if earliest else "unknown"
                ),
            },
        ))

    except Exception as exc:
        report.add(CheckResult(
            name="revenue_row_count",
            status="FAIL",
            message=f"Revenue query failed: {exc}",
            action=f"Check {tbl} table.",
        ))


# ══════════════════════════════════════════════════════════
# REPORT RENDERING
# ══════════════════════════════════════════════════════════

_ICONS = {"PASS": "[OK]", "WARN": "[!!]", "FAIL": "[XX]", "SKIP": "[--]"}

_GATE_MAP = {
    "entity_pooling": "FinancialForecastANN",
    "revenue_row_count": "RevenueForecaster (LSTM)",
    "client_history_depth": "ChurnClassifier",
    "risk_label_distribution": "RiskClassifier",
}


def render_report(report: AuditReport, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(asdict(report), indent=2, default=str)

    W = 62
    lines = [
        "",
        "=" * W,
        "  BIO-ERP Neural AI Subsystem Audit",
        f"  v{report.bio_erp_version}  |  {report.timestamp}",
        "=" * W,
    ]

    for i, chk in enumerate(report.checks, 1):
        icon = _ICONS.get(chk.status, "?")
        lines += [
            "",
            f"  {icon} [{i}/5] {chk.name}",
            f"      Status : {chk.status}",
        ]
        msg_wrap = textwrap.fill(
            chk.message, width=54,
            subsequent_indent="               ",
        )
        lines.append(f"      Result : {msg_wrap}")
        if chk.action:
            act_wrap = textwrap.fill(
                chk.action, width=54,
                subsequent_indent="               ",
            )
            lines.append(f"      Action : {act_wrap}")

        d = chk.details
        if chk.name == "risk_label_schema" and d:
            nf = len(d.get("required_found", {}))
            nm = len(d.get("required_missing", {}))
            nc = sum(
                len(v) for v in d.get("missing_columns", {}).values()
            )
            lines.append(
                f"      Tables : {nf} found  {nm} missing  "
                f"{nc} column gaps"
            )
        elif chk.name == "entity_pooling" and d:
            lines.append(
                f"      Entities : {d.get('n_entities', '?')}  "
                f"Pooled N={d.get('n_periods_total', '?')}  "
                f"KS(raw/corr)="
                f"{d.get('ks_raw_incompatible', '?')}/"
                f"{d.get('ks_corrected_incompatible', '?')}  "
                f"Rev(raw/conf)="
                f"{d.get('correlation_raw_reversals', '?')}/"
                f"{d.get('correlation_confirmed_reversals', '?')}"
            )
        elif chk.name == "client_history_depth" and d:
            lines.append(
                f"      Clients : {d.get('total_clients', '?')} total  "
                f"{d.get('pct_sufficient', 0):.0%} sufficient  "
                f"-> {d.get('recommendation', '?')}"
            )
        elif chk.name == "risk_label_distribution" and d:
            lines.append(
                f"      Labels : L={d.get('class_0_low', '?')}  "
                f"M={d.get('class_1_medium', '?')}  "
                f"H={d.get('class_2_high', '?')}  "
                f"-> {d.get('classifier_recommendation', '?')}"
            )
        elif chk.name == "revenue_row_count" and d:
            lines.append(
                f"      Revenue : {d.get('usable_days', '?')} "
                f"usable days  Gate={d.get('lstm_gate', '?')}"
            )

    s = report.summary
    lines += [
        "",
        "-" * W,
        (
            f"  SUMMARY : {s.get('PASS', 0)} passed  "
            f"{s.get('WARN', 0)} warned  "
            f"{s.get('FAIL', 0)} failed  "
            f"{s.get('SKIP', 0)} skipped"
        ),
        "",
        "  DEPLOYMENT GATES :",
    ]

    for chk in report.checks:
        if chk.name in _GATE_MAP:
            model = _GATE_MAP[chk.name]
            icon = _ICONS.get(chk.status, "?")
            lines.append(
                f"    {icon}  {model:<32s}  {chk.status}"
            )

    lines += [
        (
            "    [OK]  AnomalyAutoencoder                 "
            "DEPLOY (no gate)"
        ),
        "=" * W,
        "",
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# ORCHESTRATOR + CLI
# ══════════════════════════════════════════════════════════

async def run_audit(db_url: str, as_json: bool = False) -> AuditReport:
    if not _SQLA:
        print(
            "ERROR: sqlalchemy / asyncpg not installed.",
            file=sys.stderr,
        )
        sys.exit(2)

    report = AuditReport()
    engine = create_async_engine(db_url, echo=False)

    async def _guarded(name: str, coro_factory) -> Any:
        """Run one check; an unexpected crash becomes a FAIL result."""
        try:
            return await coro_factory()
        except Exception as exc:
            report.add(CheckResult(
                name=name, status="FAIL",
                message=f"Unhandled exception: {exc}",
                action="Check DB connection and schema.",
            ))
            return None

    try:
        async with AsyncSession(engine) as session:
            confirmed = await _guarded(
                "risk_label_schema",
                lambda: check_risk_label_schema(session, report),
            ) or set()
            await _guarded(
                "entity_pooling",
                lambda: check_entity_pooling_validity(session, report),
            )
            await _guarded(
                "client_history_depth",
                lambda: check_client_history_depth(session, report),
            )
            await _guarded(
                "risk_label_distribution",
                lambda: check_risk_label_distribution(
                    session, report, confirmed
                ),
            )
            await _guarded(
                "revenue_row_count",
                lambda: check_revenue_row_count(session, report),
            )
    finally:
        await engine.dispose()

    return report.finalize()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="BIO-ERP Neural AI Subsystem Audit"
    )
    ap.add_argument(
        "--json", action="store_true",
        help="Emit JSON report to stdout",
    )
    ap.add_argument(
        "--db-url", default=None,
        help="Async PostgreSQL URL (overrides DATABASE_URL)",
    )
    ap.add_argument(
        "--out", default=None,
        help="Write JSON report to this file path",
    )
    args = ap.parse_args()

    db_url = (
        args.db_url
        or os.environ.get("DATABASE_URL")
        or "postgresql+asyncpg://localhost/bio_erp"
    )

    report = asyncio.run(run_audit(db_url))
    output = render_report(report, as_json=args.json)
    print(output)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_report(report, as_json=True))
        print(f"  Report written -> {args.out}")

    sys.exit(report.exit_code)


if __name__ == "__main__":
    main()
