"""
P5 — HTMX Prescription Fragments (EventCore Job Pages)
Renders prescription cards as HTML for HTMX swapping.
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.config import get_settings

router = APIRouter(prefix="/api/v1/prescriptions/htmx", tags=["prescriptions-htmx"])
settings = get_settings()


def _verify_bridge_token_header(request: Request):
    """Optional: verify if X-Bridge-Token present; HTMX calls from browser may skip."""
    token = request.headers.get("X-Bridge-Token", "")
    expected = getattr(settings, "BIO_ERP_BRIDGE_TOKEN", "ec-bridge-token-dev")
    if token and token != expected:
        raise HTTPException(status_code=403, detail="Invalid bridge token")
    return True


def _ensure_prescriptions_table(db: Session):
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            analysis_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            details TEXT DEFAULT '{}',
            priority TEXT DEFAULT 'medium',
            recommended_action TEXT,
            estimated_savings REAL,
            estimated_cost REAL,
            status TEXT DEFAULT 'pending',
            source_batch_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.commit()


# ── CSS (injected once per fragment; idempotent if already present) ──
_PRESCRIPTION_CSS = """
<style>
.rx-card { border:1px solid #e5e7eb; border-radius:8px; padding:12px; margin-bottom:10px; background:#fff; box-shadow:0 1px 2px rgba(0,0,0,0.04); }
.rx-card.rx-applied { border-left:4px solid #16a34a; }
.rx-card.rx-rejected { border-left:4px solid #dc2626; opacity:0.7; }
.rx-card.rx-in_progress { border-left:4px solid #2563eb; }
.rx-card.rx-pending { border-left:4px solid #9ca3af; }
.rx-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
.rx-title { font-weight:600; font-size:14px; color:#111827; }
.rx-badge { font-size:11px; padding:2px 8px; border-radius:999px; font-weight:600; text-transform:uppercase; }
.rx-badge-high { background:#fee2e2; color:#991b1b; }
.rx-badge-medium { background:#fef3c7; color:#92400e; }
.rx-badge-low { background:#d1fae5; color:#065f46; }
.rx-meta { font-size:12px; color:#6b7280; margin-bottom:6px; }
.rx-summary { font-size:13px; color:#374151; margin-bottom:8px; line-height:1.4; }
.rx-actions { display:flex; gap:6px; flex-wrap:wrap; }
.rx-btn { font-size:12px; padding:5px 10px; border-radius:6px; border:1px solid transparent; cursor:pointer; font-weight:500; }
.rx-btn-apply { background:#16a34a; color:#fff; border-color:#16a34a; }
.rx-btn-reject { background:#fff; color:#dc2626; border-color:#dc2626; }
.rx-btn-progress { background:#2563eb; color:#fff; border-color:#2563eb; }
.rx-btn:disabled { opacity:0.5; cursor:not-allowed; }
.rx-details { margin-top:8px; padding-top:8px; border-top:1px dashed #e5e7eb; font-size:12px; color:#4b5563; }
.rx-details summary { cursor:pointer; font-weight:500; color:#6b7280; }
.rx-savings { color:#16a34a; font-weight:600; }
.rx-cost { color:#dc2626; font-weight:600; }
.rx-empty { padding:20px; text-align:center; color:#9ca3af; font-size:13px; border:2px dashed #e5e7eb; border-radius:8px; }
.rx-badge-count { display:inline-flex; align-items:center; gap:4px; font-size:11px; padding:2px 8px; border-radius:999px; background:#f3f4f6; color:#374151; font-weight:600; }
.rx-badge-count.high { background:#fee2e2; color:#991b1b; }
</style>
"""


def _priority_class(p: str) -> str:
    return f"rx-badge-{p}" if p in ("high", "medium", "low") else "rx-badge-medium"


def _status_border(status: str) -> str:
    return f"rx-{status}" if status in ("applied", "rejected", "in_progress", "pending") else "rx-pending"


def _render_card(row, request: Request) -> str:
    """Render a single prescription card as HTML string."""
    details = json.loads(row.details) if row.details else {}
    details_json = json.dumps(details, indent=2, ensure_ascii=False)
    details_html = f"<pre style='white-space:pre-wrap;word-break:break-word;font-size:11px;background:#f9fafb;padding:8px;border-radius:4px;overflow:auto;max-height:200px;'>{details_json}</pre>"

    savings_html = ""
    if row.estimated_savings:
        savings_html = f'<div class="rx-savings">💰 Estimated Savings: {row.estimated_savings:,.2f}</div>'
    cost_html = ""
    if row.estimated_cost:
        cost_html = f'<div class="rx-cost">📉 Estimated Cost: {row.estimated_cost:,.2f}</div>'

    action_html = ""
    if row.status == "pending":
        action_html = f"""
        <div class="rx-actions">
            <button class="rx-btn rx-btn-apply"
                hx-patch="/api/v1/prescriptions/htmx/{row.id}/status?status=applied"
                hx-target="#rx-card-{row.id}"
                hx-swap="outerHTML"
                hx-trigger="click"
                hx-indicator="#rx-spin-{row.id}">
                ✅ Apply
            </button>
            <button class="rx-btn rx-btn-reject"
                hx-patch="/api/v1/prescriptions/htmx/{row.id}/status?status=rejected"
                hx-target="#rx-card-{row.id}"
                hx-swap="outerHTML"
                hx-trigger="click"
                hx-confirm="Reject this prescription?"
                hx-indicator="#rx-spin-{row.id}">
                ❌ Reject
            </button>
            <button class="rx-btn rx-btn-progress"
                hx-patch="/api/v1/prescriptions/htmx/{row.id}/status?status=in_progress"
                hx-target="#rx-card-{row.id}"
                hx-swap="outerHTML"
                hx-trigger="click"
                hx-indicator="#rx-spin-{row.id}">
                🔄 In Progress
            </button>
            <span id="rx-spin-{row.id}" class="htmx-indicator" style="display:none;font-size:12px;color:#6b7280;">⏳ Updating…</span>
        </div>
        """
    else:
        action_html = f'<div class="rx-actions"><span style="font-size:12px;color:#6b7280;">Status: <strong>{row.status.upper()}</strong> — no further actions</span></div>'

    return f"""
<div id="rx-card-{row.id}" class="rx-card {_status_border(row.status)}">
    <div class="rx-header">
        <div class="rx-title">{row.title}</div>
        <div class="rx-badge {_priority_class(row.priority)}">{row.priority}</div>
    </div>
    <div class="rx-meta">
        {row.analysis_type.upper()} • {row.created_at}
    </div>
    <div class="rx-summary">{row.summary}</div>
    {savings_html}
    {cost_html}
    {action_html}
    <div class="rx-details">
        <details>
            <summary>🔍 Details & Recommended Action</summary>
            <div style="margin-top:6px;">
                <p><strong>Recommended:</strong> {row.recommended_action or "N/A"}</p>
                {details_html}
            </div>
        </details>
    </div>
</div>
"""


@router.get("/job/{job_id}", response_class=HTMLResponse)
def htmx_prescriptions_for_job(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    HTMX fragment: prescription cards for a job page.
    Usage in job template:
        <div hx-get="/api/v1/prescriptions/htmx/job/{job_id}"
             hx-trigger="load"
             hx-swap="innerHTML"></div>
    """
    _ensure_prescriptions_table(db)
    rows = db.execute(text("""
        SELECT id, job_id, analysis_type, title, summary, details, priority,
               recommended_action, estimated_savings, estimated_cost, status, created_at
        FROM prescriptions
        WHERE job_id = :job_id
        ORDER BY
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
            END,
            created_at DESC
    """), {"job_id": job_id}).mappings().all()

    if not rows:
        html = f"""
        {_PRESCRIPTION_CSS}
        <div class="rx-empty">
            <div style="font-size:24px;margin-bottom:6px;">📭</div>
            <div>No prescriptions from Bio-ERP Doctor yet.</div>
            <div style="font-size:11px;margin-top:4px;">Prescriptions appear here after OR analysis runs.</div>
        </div>
        """
        return HTMLResponse(content=html)

    cards = "\n".join([_render_card(r, request) for r in rows])
    html = f"""
{_PRESCRIPTION_CSS}
<div style="margin-bottom:8px;font-weight:600;font-size:14px;color:#374151;">
    🩺 Doctor's Prescriptions ({len(rows)})
</div>
{cards}
"""
    return HTMLResponse(content=html)


@router.patch("/{prescription_id}/status", response_class=HTMLResponse)
def htmx_update_status(
    prescription_id: int,
    status: str = Query(...),
    request: Request = Depends(),
    db: Session = Depends(get_db),
):
    """
    HTMX: update prescription status and return the refreshed card.
    Triggered by button clicks in the job page.
    """
    valid = {"pending", "applied", "rejected", "in_progress"}
    if status not in valid:
        return HTMLResponse(content=f"<div style='color:red;padding:8px;'>Invalid status: {status}</div>", status_code=422)

    _ensure_prescriptions_table(db)
    result = db.execute(text("""
        UPDATE prescriptions SET status = :status WHERE id = :id
    """), {"status": status, "id": prescription_id})
    db.commit()

    if result.rowcount == 0:
        return HTMLResponse(content="<div style='color:red;padding:8px;'>Prescription not found</div>", status_code=404)

    # Re-fetch the updated row
    row = db.execute(text("""
        SELECT id, job_id, analysis_type, title, summary, details, priority,
               recommended_action, estimated_savings, estimated_cost, status, created_at
        FROM prescriptions
        WHERE id = :id
    """), {"id": prescription_id}).mappings().first()

    if not row:
        return HTMLResponse(content="<div style='color:red;padding:8px;'>Prescription not found after update</div>", status_code=404)

    return HTMLResponse(content=_render_card(row, request))


@router.get("/badge/{job_id}", response_class=HTMLResponse)
def htmx_badge_for_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    """
    HTMX fragment: compact badge for job listing rows.
    Shows count + highest priority color.
    Usage:
        <span hx-get="/api/v1/prescriptions/htmx/badge/{job_id}"
              hx-trigger="load"
              hx-swap="outerHTML"></span>
    """
    _ensure_prescriptions_table(db)
    rows = db.execute(text("""
        SELECT priority, status FROM prescriptions WHERE job_id = :job_id
    """), {"job_id": job_id}).mappings().all()

    if not rows:
        return HTMLResponse(content="")

    count = len(rows)
    pending = sum(1 for r in rows if r.status == "pending")
    priorities = [r.priority for r in rows]
    highest = "high" if "high" in priorities else "medium" if "medium" in priorities else "low"
    high_cls = " high" if highest == "high" else ""

    label = f"{count} RX" if count > 1 else "1 RX"
    if pending:
        label += f" ({pending} pending)"

    return HTMLResponse(content=f"""
<span class="rx-badge-count{high_cls}" title="{count} prescription(s) from Bio-ERP Doctor">
    🩺 {label}
</span>
""")
