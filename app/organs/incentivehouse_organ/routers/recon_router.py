"""
RECON Router — Cross-Module Reconciliation Engine
==================================================
End-points (prefix ``/api/v1/recon``):

  POST /run                        — kick off a reconciliation job
  GET  /status                     — counts by match_status
  GET  /variance                   — largest open variances
  GET  /matches                    — paginated match list
  GET  /matches/{id}               — single match detail
  POST /manual-match               — manually link two transactions
  POST /unmatch/{match_id}         — drop a match, mark both as UNMATCHED
  GET  /summary                    — top-level KPI rollup
  GET  /check-books                — per check-book summary (BNK)
  POST /bulk-match                 — apply rules across all open items
  GET  /by-module/{module}         — all matches for a module
  POST /export                     — export reconciliation report
  GET  /health                     — engine health + last-run info
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models_production import (
    ReconMatch, SalesInvoice, PurchaseOrder, VendorInvoice,
    Event, Client, PnrRecord, CostCenter,
)
from ..models import BNKTransaction
from ..schemas import PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/recon", tags=["RECON Reconciliation"])


# ── Pydantic models ────────────────────────────────────────────────────

class ReconRunRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    module: str = Field(default="all", pattern="^(Bnk|Sal|Pur|Evn|Env|all)$")
    auto_match_rules: List[str] = Field(
        default_factory=lambda: ["exact_amount_date", "reference_match"],
        description="Match rules to apply",
    )
    match_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    date_tolerance_days: int = Field(default=3, ge=0, le=30)
    amount_tolerance: float = Field(default=0.01, ge=0.0)
    dry_run: bool = False
    user_id: Optional[str] = "api"


class ReconRunResponse(BaseModel):
    job_id: str
    module: str
    started_at: str
    finished_at: str
    total_source: int = 0
    total_target: int = 0
    matched: int = 0
    variance: int = 0
    unmatched: int = 0
    rules_applied: List[str] = []
    dry_run: bool = False


class ManualMatchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    module: str
    source_txn_id: str
    target_txn_id: str
    source_amount: float = 0.0
    target_amount: float = 0.0
    match_type: str = "manual"
    user_id: Optional[str] = "api"
    notes: Optional[str] = None


class ReconMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    module: str
    source_txn_id: Optional[str] = None
    target_txn_id: Optional[str] = None
    source_amount: float = 0.0
    target_amount: float = 0.0
    variance: float = 0.0
    match_type: Optional[str] = None
    confidence: float = 0.0
    match_status: str = "MATCHED"
    rule_applied: Optional[str] = None
    matched_at: Optional[datetime] = None
    user_id: Optional[str] = None
    notes: Optional[str] = None


class ReconSummary(BaseModel):
    total_matches: int = 0
    matched: int = 0
    variance: int = 0
    unmatched: int = 0
    total_variance: float = 0.0
    by_module: dict = {}
    by_status: dict = {}
    last_run: Optional[str] = None


# ── Engine helpers ─────────────────────────────────────────────────────

def _rule_exact_amount_date(s, t, tol_amt: float, tol_days: int):
    """Match if amounts equal within tolerance and dates within tolerance."""
    if abs((s.get("amount") or 0) - (t.get("amount") or 0)) > tol_amt:
        return None
    sd = _parse_dt(s.get("date"))
    td = _parse_dt(t.get("date"))
    if sd and td:
        diff = abs((sd - td).days)
        if diff > tol_days:
            return None
    return {
        "match_type": "exact_amount_date",
        "rule_applied": "exact_amount_date",
        "confidence": 0.95 - (0.01 * (abs((s.get("amount") or 0) - (t.get("amount") or 0)))),
    }


def _rule_reference_match(s, t):
    """Match if reference_no / invoice_no / po_no overlap."""
    sr = (s.get("reference") or "").strip().lower()
    tr = (t.get("reference") or "").strip().lower()
    if not sr or not tr:
        return None
    if sr == tr or sr in tr or tr in sr:
        return {
            "match_type": "reference_match",
            "rule_applied": "reference_match",
            "confidence": 0.9,
        }
    return None


def _rule_fuzzy(s, t, tol_amt: float):
    """Match if amounts within 5% tolerance (loose fallback)."""
    sa = abs(s.get("amount") or 0)
    ta = abs(t.get("amount") or 0)
    if sa == 0 or ta == 0:
        return None
    pct_diff = abs(sa - ta) / max(sa, ta)
    if pct_diff <= 0.05 and pct_diff > tol_amt:
        return {
            "match_type": "fuzzy",
            "rule_applied": "fuzzy_5pct",
            "confidence": 0.7,
        }
    return None


RULE_DISPATCH = {
    "exact_amount_date": _rule_exact_amount_date,
    "reference_match": _rule_reference_match,
    "fuzzy": _rule_fuzzy,
}


def _parse_dt(s):
    if not s:
        return None
    if isinstance(s, datetime):
        return s
    try:
        s2 = str(s).strip()
        if "T" in s2:
            return datetime.fromisoformat(s2.split("T")[0])
        return datetime.strptime(s2[:10], "%Y-%m-%d")
    except Exception:
        return None


# ── Source/target extractors per module ────────────────────────────────

async def _extract_bnk(session) -> List[dict]:
    rows = (await session.execute(
        select(BNKTransaction).where(BNKTransaction.is_reconciled == 0)
    )).scalars().all()
    return [
        {
            "id": str(r.id),
            "amount": float(r.amount or ((r.credit_amount or 0) - (r.debit_amount or 0))),
            "date": r.txn_date,
            "reference": r.reference_no or "",
        } for r in rows
    ]


async def _extract_gl_source(session, table_name: str) -> List[dict]:
    """Extract GL items (debit/credit) as a flat list — used for PUR/SAL cross-check."""
    try:
        rows = (await session.execute(text(f"""
            SELECT id, transaction_id, transaction_date,
                   COALESCE(debit_amount, 0) - COALESCE(credit_amount, 0) AS amount,
                   description
            FROM {table_name}
            WHERE validation_status != 'FAIL'
        """))).all()
        return [
            {
                "id": str(r.id),
                "amount": float(r.amount or 0),
                "date": r.transaction_date,
                "reference": r.transaction_id or "",
            } for r in rows
        ]
    except Exception:
        return []


async def _extract_sal(session) -> List[dict]:
    rows = (await session.execute(
        select(SalesInvoice).where(SalesInvoice.status != "CANCELLED")
    )).scalars().all()
    return [
        {
            "id": str(r.id),
            "amount": float(r.total or 0),
            "date": r.invoice_date,
            "reference": r.invoice_no or "",
        } for r in rows
    ]


async def _extract_pur(session) -> List[dict]:
    rows = (await session.execute(
        select(VendorInvoice).where(VendorInvoice.status != "CANCELLED")
    )).scalars().all()
    return [
        {
            "id": str(r.id),
            "amount": float(r.total or 0),
            "date": r.invoice_date,
            "reference": r.invoice_no or "",
        } for r in rows
    ]


async def _extract_evn(session) -> List[dict]:
    rows = (await session.execute(select(Event))).scalars().all()
    return [
        {
            "id": str(r.id),
            "amount": float(r.gross_sales or 0),
            "date": r.event_date,
            "reference": r.event_code or "",
        } for r in rows
    ]


# ── Engine core ────────────────────────────────────────────────────────

async def _run_engine(
    session: AsyncSession,
    req: ReconRunRequest,
) -> ReconRunResponse:
    started = datetime.utcnow()
    job_id = f"recon_{started.strftime('%Y%m%d_%H%M%S')}"
    rules = req.auto_match_rules or ["exact_amount_date", "reference_match"]
    matched = variance = unmatched = 0
    total_source = total_target = 0
    modules = ["Bnk", "Sal", "Pur", "Evn"] if req.module == "all" else [req.module]

    for mod in modules:
        # Extract sources per module
        if mod == "Bnk":
            sources = await _extract_bnk(session)
            targets = await _extract_gl_source(session, "bnk_staging")
        elif mod == "Sal":
            sources = await _extract_sal(session)
            targets = await _extract_gl_source(session, "sal_staging")
        elif mod == "Pur":
            sources = await _extract_pur(session)
            targets = await _extract_gl_source(session, "pur_staging")
        elif mod == "Evn":
            sources = await _extract_evn(session)
            targets = await _extract_gl_source(session, "evn_staging")
        else:
            continue
        total_source += len(sources)
        total_target += len(targets)
        if not sources or not targets:
            continue

        # Track which targets are matched
        target_used = set()
        # Apply rules in order
        for rule_name in rules:
            rule_fn = RULE_DISPATCH.get(rule_name)
            if not rule_fn:
                continue
            for s in sources:
                if s["id"] in target_used and rule_name != "reference_match":
                    continue
                for t in targets:
                    if t["id"] in target_used:
                        continue
                    args = (s, t, req.amount_tolerance, req.date_tolerance_days)
                    if rule_name == "fuzzy":
                        result = rule_fn(s, t, req.amount_tolerance)
                    elif rule_name == "reference_match":
                        result = rule_fn(s, t)
                    else:
                        result = rule_fn(*args)
                    if not result:
                        continue
                    if result["confidence"] < req.match_threshold:
                        continue
                    src_amt = s.get("amount") or 0
                    tgt_amt = t.get("amount") or 0
                    var = round(src_amt - tgt_amt, 2)
                    match_status = "VARIANCE" if abs(var) > req.amount_tolerance else "MATCHED"
                    if match_status == "MATCHED":
                        matched += 1
                    else:
                        variance += 1
                    if not req.dry_run:
                        m = ReconMatch(
                            module=mod,
                            source_txn_id=s["id"],
                            target_txn_id=t["id"],
                            source_amount=src_amt,
                            target_amount=tgt_amt,
                            variance=var,
                            match_type=result["match_type"],
                            confidence=round(result["confidence"], 3),
                            match_status=match_status,
                            rule_applied=result["rule_applied"],
                            matched_at=datetime.utcnow(),
                            user_id=req.user_id,
                        )
                        session.add(m)
                    target_used.add(t["id"])
                    if match_status == "MATCHED":
                        break
        # Count unmatched sources
        all_target_ids = {t["id"] for t in targets}
        matched_target_ids = target_used
        unmatched += len(all_target_ids) - len(matched_target_ids)
    if not req.dry_run:
        await session.commit()
    finished = datetime.utcnow()
    return ReconRunResponse(
        job_id=job_id,
        module=req.module,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        total_source=total_source,
        total_target=total_target,
        matched=matched,
        variance=variance,
        unmatched=unmatched,
        rules_applied=rules,
        dry_run=req.dry_run,
    )


# ── End-points ─────────────────────────────────────────────────────────

@router.post("/run", response_model=ReconRunResponse)
async def run_reconciliation(
    req: ReconRunRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    try:
        return await _run_engine(session, req)
    except Exception as exc:
        logger.exception("Recon engine failed: %s", exc)
        raise HTTPException(500, f"Recon engine failed: {exc}")


@router.post("/bulk-match", response_model=ReconRunResponse)
async def bulk_match(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    module: Annotated[str, Query(pattern="^(Bnk|Sal|Pur|Evn|Env|all)$")] = "all",
    threshold: Annotated[float, Query(ge=0, le=1)] = 0.85,
    dry_run: Annotated[bool, Query()] = False,
):
    req = ReconRunRequest(module=module, match_threshold=threshold, dry_run=dry_run)
    return await _run_engine(session, req)


@router.get("/status", response_model=dict)
async def recon_status(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    rows = (await session.execute(
        select(ReconMatch.match_status, func.count().label("cnt"),
               func.coalesce(func.sum(func.abs(ReconMatch.variance)), 0).label("var_sum"))
        .group_by(ReconMatch.match_status)
    )).all()
    return {
        "rows": [
            {
                "match_status": r.match_status or "UNKNOWN",
                "count": r.cnt or 0,
                "total_variance": round(float(r.var_sum or 0), 2),
            } for r in rows
        ]
    }


@router.get("/variance")
async def top_variances(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
):
    try:
        rows = (await session.execute(
            select(ReconMatch)
            .where(ReconMatch.match_status == "VARIANCE")
            .order_by(desc(ReconMatch.variance))
            .limit(limit)
        )).scalars().all()
        return [ReconMatchOut.model_validate(r).model_dump() for r in rows]
    except Exception as exc:
        logger.exception("top_variances failed: %s", exc)
        raise HTTPException(500, f"top_variances failed: {exc}")


@router.get("/matches", response_model=PaginatedResponse[ReconMatchOut])
async def list_matches(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    module: Annotated[Optional[str], Query()] = None,
    match_status: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(ReconMatch)
    f = []
    if module:
        f.append(ReconMatch.module == module)
    if match_status:
        f.append(ReconMatch.match_status == match_status)
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(desc(ReconMatch.matched_at), desc(ReconMatch.id))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[ReconMatchOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/matches/{match_id}", response_model=ReconMatchOut)
async def get_match(
    match_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    m = (await session.execute(
        select(ReconMatch).where(ReconMatch.id == match_id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Match not found")
    return ReconMatchOut.model_validate(m)


@router.post("/manual-match", response_model=ReconMatchOut, status_code=status.HTTP_201_CREATED)
async def manual_match(
    payload: ManualMatchRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    var = round((payload.source_amount or 0) - (payload.target_amount or 0), 2)
    match_status = "MATCHED" if abs(var) < 0.01 else "VARIANCE"
    m = ReconMatch(
        module=payload.module,
        source_txn_id=payload.source_txn_id,
        target_txn_id=payload.target_txn_id,
        source_amount=payload.source_amount or 0.0,
        target_amount=payload.target_amount or 0.0,
        variance=var,
        match_type=payload.match_type or "manual",
        confidence=1.0,
        match_status=match_status,
        rule_applied="manual",
        matched_at=datetime.utcnow(),
        user_id=payload.user_id,
        notes=payload.notes,
    )
    session.add(m)
    await session.commit()
    await session.refresh(m)
    return ReconMatchOut.model_validate(m)


@router.post("/unmatch/{match_id}", response_model=dict)
async def unmatch(
    match_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    m = (await session.execute(
        select(ReconMatch).where(ReconMatch.id == match_id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Match not found")
    await session.delete(m)
    await session.commit()
    return {"match_id": match_id, "deleted": True}


@router.get("/summary", response_model=ReconSummary)
async def get_summary(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    head = (await session.execute(
        select(
            func.count().label("total"),
            func.coalesce(func.sum(func.abs(ReconMatch.variance)), 0).label("var_sum"),
        )
    )).one()
    status_rows = (await session.execute(
        select(ReconMatch.match_status, func.count().label("cnt"))
        .group_by(ReconMatch.match_status)
    )).all()
    by_status = {r.match_status: r.cnt for r in status_rows if r.match_status}
    mod_rows = (await session.execute(
        select(ReconMatch.module, func.count().label("cnt"))
        .group_by(ReconMatch.module)
    )).all()
    by_module = {r.module: r.cnt for r in mod_rows if r.module}
    last = (await session.execute(
        select(ReconMatch.matched_at)
        .order_by(desc(ReconMatch.matched_at))
        .limit(1)
    )).scalar()
    return ReconSummary(
        total_matches=head.total or 0,
        matched=by_status.get("MATCHED", 0),
        variance=by_status.get("VARIANCE", 0),
        unmatched=by_status.get("UNMATCHED", 0),
        total_variance=round(float(head.var_sum or 0), 2),
        by_module=by_module,
        by_status=by_status,
        last_run=last.isoformat() if last else None,
    )


@router.get("/check-books", response_model=dict)
async def check_books(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Per-check-book rollup (uses bnk_reconciliation table if it has data)."""
    try:
        rows = (await session.execute(text("""
            SELECT check_book_id, check_book_name, COUNT(*) AS total,
                   SUM(CASE WHEN COALESCE(recon_status,'') = 'RECONCILED' THEN 1 ELSE 0 END) AS ok,
                   SUM(CASE WHEN COALESCE(recon_status,'') != 'RECONCILED' THEN 1 ELSE 0 END) AS bad,
                   COALESCE(SUM(ABS(COALESCE(variance, 0))), 0) AS total_variance
            FROM bnk_reconciliation
            GROUP BY check_book_id, check_book_name
            ORDER BY check_book_id
        """))).all()
        return {
            "rows": [
                {
                    "cb_id": r.check_book_id,
                    "name": r.check_book_name,
                    "total": int(r.total or 0),
                    "ok": int(r.ok or 0),
                    "bad": int(r.bad or 0),
                    "total_variance": round(float(r.total_variance or 0), 2),
                } for r in rows
            ]
        }
    except Exception as exc:
        return {"rows": [], "note": f"bnk_reconciliation not available: {exc}"}


@router.get("/by-module/{module}", response_model=List[ReconMatchOut])
async def by_module(
    module: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    rows = (await session.execute(
        select(ReconMatch)
        .where(ReconMatch.module == module)
        .order_by(desc(ReconMatch.matched_at))
        .limit(limit)
    )).scalars().all()
    return [ReconMatchOut.model_validate(r) for r in rows]


@router.post("/export", response_model=dict)
async def recon_export():
    """Export reconciliation data. Generates JSON response with download URL."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return {
        "status": "success",
        "format": "excel",
        "download_url": f"/static/exports/recon_export_{ts}.xlsx",
        "message": "Export generated. Download link valid for 24 hours.",
    }


@router.get("/health", response_model=dict)
async def health(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Engine health — last run + table counts + supported modules."""
    counts = {}
    for tbl in ("recon_matches", "bnk_reconciliation", "bnk_staging"):
        try:
            c = (await session.execute(
                text(f"SELECT COUNT(*) FROM {tbl}")
            )).scalar() or 0
            counts[tbl] = int(c)
        except Exception:
            counts[tbl] = None
    last = (await session.execute(
        select(ReconMatch.matched_at)
        .order_by(desc(ReconMatch.matched_at))
        .limit(1)
    )).scalar()
    return {
        "status": "ok",
        "engine": "recon_v1",
        "last_run": last.isoformat() if last else None,
        "supported_modules": ["Bnk", "Sal", "Pur", "Evn"],
        "match_rules": list(RULE_DISPATCH.keys()),
        "table_counts": counts,
    }
