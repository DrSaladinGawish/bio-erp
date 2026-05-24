from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user, RequirePermission
from app.models.auth import User
from app.services.cost_engine import CostEngine
from app.services.report_engine import generate_executive_summary
from app.models import Event, Client, Branch
from app.core.branch_filter import BranchFilter, get_optional_branch_filter
from app.services.event_bridge import EventBridge
from app.models.event_management import EventLog, MigrationStatus

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard HTMX"])


def _card(label: str, value: str, sub: str = "") -> str:
    return f'<div class="card"><div class="label">{label}</div><div class="value">{value}</div>{"<div class=sub>" + sub + "</div>" if sub else ""}</div>'


@router.get("/stats-bar", response_class=HTMLResponse)
async def stats_bar(
    branch_filter: BranchFilter = Depends(get_optional_branch_filter),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    bf = branch_filter
    event_q = select(func.count(Event.id))
    active_q = select(func.count(Event.id)).where(
        Event.status.in_(["IN_PROGRESS", "APPROVED"])
    )
    revenue_q = select(func.coalesce(func.sum(Event.total_revenue), 0))
    client_q = select(func.count(Client.id)).where(Client.is_active)
    branch_q = select(func.count(Branch.id))

    if bf.is_filtered:
        event_q = event_q.where(Event.branch_id == bf.branch_id)
        active_q = active_q.where(Event.branch_id == bf.branch_id)
        revenue_q = revenue_q.where(Event.branch_id == bf.branch_id)
        branch_q = branch_q.where(Branch.id == bf.branch_id)

    event_count = await db.scalar(event_q) or 0
    active = await db.scalar(active_q) or 0
    revenue = await db.scalar(revenue_q) or 0
    clients = await db.scalar(client_q) or 0
    branches = await db.scalar(branch_q) or 0
    lines = [
        _card("Total Events", str(event_count)),
        _card("Active Events", str(active)),
        _card("Total Clients", str(clients)),
        _card("Revenue (EGP)", f"{revenue:,.0f}"),
        _card("Branches", str(branches)),
    ]
    return "".join(lines)


@router.get("/branch-cards", response_class=HTMLResponse)
async def branch_cards(
    branch_filter: BranchFilter = Depends(get_optional_branch_filter),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    data = await CostEngine.get_branch_profitability(
        db, branch_id=branch_filter.branch_id
    )
    if not data:
        return "<p style='color:#64748b;'>No branch data available</p>"
    rows = ""
    for b in data:
        m_class = (
            "badge-green"
            if b["gross_margin_pct"] > 15
            else "badge-yellow"
            if b["gross_margin_pct"] > 5
            else "badge-red"
        )
        rows += f"<tr><td>{b['branch_name']}</td><td>{b['revenue']:,.0f}</td><td>{b['gross_profit']:,.0f}</td><td><span class='badge {m_class}'>{b['gross_margin_pct']}%</span></td><td>{b['event_count']}</td></tr>"
    return f"<table><thead><tr><th>Branch</th><th>Revenue</th><th>Gross Profit</th><th>Margin</th><th>Events</th></tr></thead><tbody>{rows}</tbody></table>"


@router.get("/variance-table", response_class=HTMLResponse)
async def variance_table(
    branch_filter: BranchFilter = Depends(get_optional_branch_filter),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    var = await CostEngine.get_variance_report(db, branch_id=branch_filter.branch_id)
    rows = ""
    for r in var.get("rows", [])[:10]:
        flag_class = (
            "badge-red"
            if r["flag"] == "investigate"
            else "badge-yellow"
            if r["flag"] == "ok"
            else "badge-green"
        )
        rows += f"<tr><td>{r['cost_center_name']}</td><td>{r['coa_account_name']}</td><td>{r['budgeted']:,.0f}</td><td>{r['actual']:,.0f}</td><td><span class='badge {flag_class}'>{r['variance_pct']}%</span></td></tr>"
    if not rows:
        return "<p style='color:#64748b;'>No variance data</p>"
    return f"<table><thead><tr><th>Center</th><th>Account</th><th>Budget</th><th>Actual</th><th>Var%</th></tr></thead><tbody>{rows}</tbody></table>"


@router.post("/ai-query", response_class=HTMLResponse)
async def ai_query_fragment(
    request: Request,
    branch_filter: BranchFilter = Depends(get_optional_branch_filter),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    from app.services.local_ai_engine import (
        get_ai_engine,
        validate_query,
        execute_safe_query,
        format_results,
    )
    from app.routers.ai_bridge import _route_question
    import json

    body = await request.body()
    try:
        data = json.loads(body)
        question = data.get("question", "") or (await request.form()).get(
            "question", ""
        )
    except Exception:
        question = ""

    if not question:
        return "<p style='color:#ef4444;'>Please enter a question.</p>"

    route = _route_question(question)
    if route == "branch_profitability":
        data = await CostEngine.get_branch_profitability(
            db, branch_id=branch_filter.branch_id
        )
        lines = ["<strong>Branch Profitability</strong><br>"]
        for row in data:
            lines.append(
                f"{row['branch_name']}: Rev {row['revenue']:,.0f} | GP {row['gross_profit']:,.0f} ({row['gross_margin_pct']}%)<br>"
            )
        return "".join(lines)
    if route == "variance_report":
        data = await CostEngine.get_variance_report(
            db, branch_id=branch_filter.branch_id
        )
        lines = [f"<strong>Variance Report â€” {data['period_label']}</strong><br>"]
        for row in data["rows"][:10]:
            lines.append(
                f"{row['cost_center_name']}/{row['coa_account_name']}: Budget {row['budgeted']:,.0f} | Actual {row['actual']:,.0f} | <span class='badge badge-red'>{row['variance_pct']}%</span><br>"
            )
        return "".join(lines)

    engine = get_ai_engine()
    try:
        sql = await engine.generate_sql(question)
    except Exception as e:
        return f"<p style='color:#ef4444;'>AI engine unavailable: {e}</p>"
    valid, err = validate_query(sql)
    if not valid:
        return f"<p style='color:#ef4444;'>Invalid query: {err}</p><pre style='font-size:11px;color:#94a3b8;'>{sql}</pre>"
    try:
        rows = await execute_safe_query(db, sql)
    except Exception as e:
        return f"<p style='color:#ef4444;'>Query failed: {e}</p><pre style='font-size:11px;color:#94a3b8;'>{sql}</pre>"
    result = format_results(rows)
    return f"<pre style='font-size:13px;'>{result}</pre>"


@router.get("/executive-fragment", response_class=HTMLResponse)
async def executive_fragment(
    branch_filter: BranchFilter = Depends(get_optional_branch_filter),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    summary = await generate_executive_summary(db, branch_id=branch_filter.branch_id)
    fh = summary["financial_health"]
    flag = (
        "badge-green"
        if abs(fh["variance_pct"]) < 5
        else "badge-yellow"
        if abs(fh["variance_pct"]) < 10
        else "badge-red"
    )
    return f"""
    <div>Period: <strong>{summary["period_label"]}</strong></div>
    <div style="margin-top:8px;">Budget: {fh["total_budgeted"]:,.0f}</div>
    <div>Actual: {fh["total_actual"]:,.0f}</div>
    <div>Variance: <span class='badge {flag}'>{fh["variance_pct"]}%</span></div>
    <div style="margin-top:8px;">Alerts: <strong>{summary["alert_count"]}</strong></div>
    """


@router.get("/health-bar", response_class=HTMLResponse)
async def health_bar():
    return '<span class="badge badge-green">Connected</span>'


@router.get("/health-detail", response_class=HTMLResponse)
async def health_detail():
    from app.services.health import HealthCheck

    h = await HealthCheck.full_check()
    items = ""
    for name, check in h["checks"].items():
        cls = (
            "badge-green"
            if check.get("status") == "healthy"
            else "badge-yellow"
            if check.get("status") == "degraded"
            else "badge-red"
        )
        label = check.get("status", "unknown")
        latency = check.get("latency_ms")
        lat_str = f" ({latency}ms)" if latency else ""
        items += f"<div style='margin:4px 0;'><span class='badge {cls}'>{label}</span> {name}{lat_str}</div>"
    return f'<div style="font-size:13px;">{items}</div>'


@router.get("/event-stream", response_class=HTMLResponse)
async def event_stream(
    branch_filter: BranchFilter = Depends(get_optional_branch_filter),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    q = select(EventLog).order_by(EventLog.timestamp.desc()).limit(20)
    if branch_filter.is_filtered:
        q = q.where(EventLog.branch_id == branch_filter.branch_id)
    result = await db.execute(q)
    events = result.scalars().all()

    if not events:
        return "<p style='color:#64748b;'>No recent events</p>"

    rows = ""
    for e in events:
        sev_class = (
            "badge-red"
            if e.severity == "critical"
            else "badge-yellow"
            if e.severity == "warning"
            else "badge-blue"
        )
        rows += f"<tr><td><span class='badge {sev_class}'>{e.severity}</span></td><td>{e.source_component}</td><td>{e.event_type}</td><td style='font-size:11px;color:#94a3b8;'>{(e.timestamp.isoformat()[:19] if e.timestamp else '')}</td></tr>"
    return f"<table><thead><tr><th>Sev</th><th>Source</th><th>Type</th><th>Time</th></tr></thead><tbody>{rows}</tbody></table>"


@router.get("/event-summary", response_class=HTMLResponse)
async def event_summary(
    branch_filter: BranchFilter = Depends(get_optional_branch_filter),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("dashboard.read")),
):
    data = await EventBridge.branch_event_aggregator(
        db, branch_id=branch_filter.branch_id
    )
    if not data:
        return "<p style='color:#64748b;'>No event data</p>"
    cards = ""
    for d in data[:5]:
        "badge-red" if d["critical"] > 0 else "badge-green"
        cards += _card(
            d["date"],
            str(d["total"]),
            f"âš  {d['critical']} critical, {d['warning']} warnings",
        )
    return "".join(cards)


@router.get("/sync-status", response_class=HTMLResponse)
async def sync_status_fragment(
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count(EventLog.id))) or 0
    synced = (
        await db.scalar(
            select(func.count(EventLog.id)).where(
                EventLog.migration_status == MigrationStatus.synced.value
            )
        )
        or 0
    )
    failed = (
        await db.scalar(
            select(func.count(EventLog.id)).where(
                EventLog.migration_status == MigrationStatus.failed.value
            )
        )
        or 0
    )

    pct = round(synced / total * 100, 1) if total else 100.0
    if failed > 0:
        cls, label = "badge-red", "Degraded"
    elif pct < 100:
        cls, label = "badge-yellow", "Syncing"
    else:
        cls, label = "badge-green", "Healthy"

    return f'<span class="badge {cls}">{label}</span> <span style="font-size:12px;color:#94a3b8;">{synced}/{total} ({pct}%)</span>'
