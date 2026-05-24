import asyncio
from datetime import datetime
from datetime import timezone
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.event import Event
from app.models.client import Client
from app.models.supplier import Supplier, RFQ, PurchaseOrder
from app.models.einvoice import EInvoiceRegister
from app.models.branch import Branch
from app.models.audit import AuditLog

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

# === WEBSOCKET CONNECTIONS ===
active_connections: list[WebSocket] = []


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast(data: dict):
    dead = []
    for conn in active_connections:
        try:
            await conn.send_json(data)
        except Exception:
            dead.append(conn)
    for conn in dead:
        active_connections.remove(conn)


# === DASHBOARD HTML PAGE ===

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BIO ERP Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
  .header h1 { font-size: 24px; background: linear-gradient(135deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .status { display: flex; gap: 16px; align-items: center; }
  .status .dot { width: 10px; height: 10px; border-radius: 50%; background: #22c55e; display: inline-block; animation: pulse 2s infinite; }
  @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .card { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }
  .card .label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
  .card .value { font-size: 28px; font-weight: 700; }
  .card .sub { font-size: 12px; color: #64748b; margin-top: 4px; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
  .table-card { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }
  .table-card h3 { font-size: 14px; color: #94a3b8; margin-bottom: 12px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; padding: 8px 4px; color: #64748b; font-weight: 500; border-bottom: 1px solid #334155; }
  td { padding: 8px 4px; border-bottom: 1px solid #1e293b; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .badge-green { background: #166534; color: #86efac; }
  .badge-yellow { background: #854d0e; color: #fde047; }
  .badge-red { background: #991b1b; color: #fca5a5; }
  .badge-blue { background: #1e3a5f; color: #93c5fd; }
  .footer { text-align: center; color: #475569; font-size: 12px; padding: 20px; }
</style>
</head>
<body>
<div class="header">
  <h1>BIO ERP Dashboard</h1>
  <div class="status">
    <span class="dot"></span>
    <span id="lastUpdate">Connecting...</span>
  </div>
</div>

<div class="grid" id="statsGrid">
  <div class="card"><div class="label">Total Events</div><div class="value" id="totalEvents">â€”</div></div>
  <div class="card"><div class="label">Active Events</div><div class="value" id="activeEvents">â€”</div></div>
  <div class="card"><div class="label">Total Revenue</div><div class="value" id="totalRevenue">â€”</div><div class="sub">EGP</div></div>
  <div class="card"><div class="label">Total Clients</div><div class="value" id="totalClients">â€”</div></div>
  <div class="card"><div class="label">Total Suppliers</div><div class="value" id="totalSuppliers">â€”</div></div>
  <div class="card"><div class="label">Pending RFQs</div><div class="value" id="pendingRfqs">â€”</div></div>
  <div class="card"><div class="label">ETA Success Rate</div><div class="value" id="etaSuccess">â€”</div><div class="sub">e-invoice compliance</div></div>
  <div class="card"><div class="label">Avg Event Value</div><div class="value" id="avgEventValue">â€”</div><div class="sub">EGP</div></div>
</div>

<div class="row">
  <div class="table-card">
    <h3>Recent Events</h3>
    <table><thead><tr><th>Code</th><th>Client</th><th>Status</th><th>Revenue</th></tr></thead><tbody id="recentEvents"></tbody></table>
  </div>
  <div class="table-card">
    <h3>Top Clients</h3>
    <table><thead><tr><th>Client</th><th>Events</th><th>Revenue</th></tr></thead><tbody id="topClients"></tbody></table>
  </div>
</div>

<div class="footer">
  BIO ERP v1.0.0 | <span id="footerTime"></span> | Live WebSocket
</div>

<script>
const ws = new WebSocket(`ws://${location.host}/api/v1/dashboard/ws`);
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
  document.getElementById('footerTime').textContent = new Date().toLocaleString();
  if (data.total_events !== undefined) {
    document.getElementById('totalEvents').textContent = data.total_events.toLocaleString();
    document.getElementById('activeEvents').textContent = data.active_events;
    document.getElementById('totalRevenue').textContent = (data.total_revenue_egp || 0).toLocaleString();
    document.getElementById('totalClients').textContent = data.total_clients;
    document.getElementById('totalSuppliers').textContent = data.total_suppliers;
    document.getElementById('pendingRfqs').textContent = data.pending_rfqs;
    document.getElementById('etaSuccess').textContent = (data.eta_success_rate || 0).toFixed(1) + '%';
    document.getElementById('avgEventValue').textContent = (data.avg_event_value || 0).toLocaleString();
  }
  if (data.recent_events) {
    document.getElementById('recentEvents').innerHTML = data.recent_events.map(e =>
      `<tr><td>${e.event_code}</td><td>${e.client_name || 'â€”'}</td><td><span class="badge badge-${e.status === 'COMPLETED' ? 'green' : e.status === 'IN_PROGRESS' ? 'blue' : e.status === 'APPROVED' ? 'green' : 'yellow'}">${e.status}</span></td><td>${(e.total_revenue || 0).toLocaleString()}</td></tr>`
    ).join('');
  }
  if (data.top_clients) {
    document.getElementById('topClients').innerHTML = data.top_clients.map(c =>
      `<tr><td>${c.name_en}</td><td>${c.event_count}</td><td>${(c.total_revenue || 0).toLocaleString()}</td></tr>`
    ).join('');
  }
};
ws.onopen = () => { document.getElementById('lastUpdate').textContent = 'Live'; };
</script>
</body>
</html>
"""


# === STATS ENDPOINTS ===


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    event_count = await db.scalar(select(func.count(Event.id)))
    active_count = await db.scalar(
        select(func.count(Event.id)).where(
            Event.status.in_(["IN_PROGRESS", "APPROVED"])
        )
    )
    client_count = await db.scalar(
        select(func.count(Client.id)).where(Client.is_active)
    )
    supplier_count = await db.scalar(
        select(func.count(Supplier.id)).where(Supplier.is_active)
    )
    total_revenue = await db.scalar(
        select(func.coalesce(func.sum(Event.total_revenue), 0))
    )
    total_cost = await db.scalar(select(func.coalesce(func.sum(Event.total_cost), 0)))
    rfq_count = await db.scalar(select(func.count(RFQ.id)).where(RFQ.status == "DRAFT"))
    po_count = await db.scalar(select(func.count(PurchaseOrder.id)))
    eta_pending = await db.scalar(
        select(func.count(EInvoiceRegister.id)).where(
            EInvoiceRegister.eta_status == "PENDING"
        )
    )
    eta_accepted = await db.scalar(
        select(func.count(EInvoiceRegister.id)).where(
            EInvoiceRegister.eta_status == "SUBMITTED"
        )
    )
    eta_rejected = await db.scalar(
        select(func.count(EInvoiceRegister.id)).where(
            EInvoiceRegister.eta_status == "REJECTED"
        )
    )
    total_eta = (eta_accepted or 0) + (eta_rejected or 0)
    eta_rate = (eta_accepted / total_eta * 100) if total_eta > 0 else 100.0
    avg_value = round((total_revenue or 0) / (event_count or 1), 2)

    branch_stats = []
    branches = await db.execute(select(Branch))
    for branch in branches.scalars():
        b_count = await db.scalar(
            select(func.count(Event.id)).where(Event.branch_id == branch.id)
        )
        b_rev = await db.scalar(
            select(func.coalesce(func.sum(Event.total_revenue), 0)).where(
                Event.branch_id == branch.id
            )
        )
        branch_stats.append(
            {
                "name": branch.name_en,
                "code": branch.code,
                "events": b_count or 0,
                "revenue": round(b_rev or 0, 2),
            }
        )

    return {
        "total_events": event_count or 0,
        "active_events": active_count or 0,
        "total_clients": client_count or 0,
        "total_suppliers": supplier_count or 0,
        "total_revenue_egp": round(total_revenue or 0, 2),
        "total_cost_egp": round(total_cost or 0, 2),
        "gross_profit": round((total_revenue or 0) - (total_cost or 0), 2),
        "avg_event_value": avg_value,
        "pending_rfqs": rfq_count or 0,
        "pending_pos": po_count or 0,
        "eta_pending": eta_pending or 0,
        "eta_accepted": eta_accepted or 0,
        "eta_rejected": eta_rejected or 0,
        "eta_success_rate": round(eta_rate, 2),
        "branches": branch_stats,
    }


@router.get("/top-clients")
async def top_clients(limit: int = Query(5), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Client.id,
            Client.name_en,
            Client.name_ar,
            func.count(Event.id).label("event_count"),
            func.coalesce(func.sum(Event.total_revenue), 0).label("total_revenue"),
        )
        .join(Event, Event.client_id == Client.id)
        .group_by(Client.id)
        .order_by(func.sum(Event.total_revenue).desc())
        .limit(limit)
    )
    return [
        {
            "id": r.id,
            "name_en": r.name_en,
            "name_ar": r.name_ar,
            "event_count": r.event_count,
            "total_revenue": round(r.total_revenue, 2),
        }
        for r in result.all()
    ]


@router.get("/recent-events")
async def recent_events(limit: int = Query(10), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Event).order_by(Event.created_at.desc()).limit(limit)
    )
    events = result.scalars().all()
    data = []
    for e in events:
        client = await db.get(Client, e.client_id)
        data.append(
            {
                "id": e.id,
                "event_code": e.event_code,
                "name_en": e.name_en,
                "status": e.status,
                "total_revenue": e.total_revenue,
                "client_name": client.name_en if client else None,
                "branch_id": e.branch_id,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
        )
    return data


@router.get("/supplier-performance")
async def supplier_performance(
    limit: int = Query(10), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Supplier)
        .where(Supplier.is_active)
        .order_by(Supplier.rating.desc())
        .limit(limit)
    )
    return [
        {
            "id": s.id,
            "name_en": s.name_en,
            "service_category": s.service_category,
            "rating": s.rating,
        }
        for s in result.scalars().all()
    ]


@router.get("/eta-compliance")
async def eta_compliance(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(EInvoiceRegister.id)))
    by_status = {}
    statuses = ["PENDING", "SUBMITTED", "VALID", "REJECTED"]
    for s in statuses:
        c = await db.scalar(
            select(func.count(EInvoiceRegister.id)).where(
                EInvoiceRegister.eta_status == s
            )
        )
        by_status[s] = c or 0
    return {"total": total or 0, "by_status": by_status}


@router.get("/branch-comparison")
async def branch_comparison(db: AsyncSession = Depends(get_db)):
    branches = await db.execute(select(Branch))
    result = []
    for branch in branches.scalars():
        events = await db.execute(select(Event).where(Event.branch_id == branch.id))
        event_list = events.scalars().all()
        revenue = sum(e.total_revenue or 0 for e in event_list)
        cost = sum(e.total_cost or 0 for e in event_list)
        result.append(
            {
                "id": branch.id,
                "code": branch.code,
                "name": branch.name_en,
                "country": branch.country,
                "vat_rate": branch.vat_rate,
                "events": len(event_list),
                "revenue": round(revenue, 2),
                "cost": round(cost, 2),
                "profit": round(revenue - cost, 2),
            }
        )
    return result


@router.get("/audit-trail")
async def audit_trail(limit: int = Query(20), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    )
    return [
        {
            "id": a.id,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "actor_name": a.actor_name,
            "action": a.action,
            "target_type": a.target_type,
            "description": a.description,
        }
        for a in result.scalars().all()
    ]


# === BACKGROUND BROADCASTER ===


async def broadcast_dashboard_updates():
    from app.database import async_session_factory

    while True:
        try:
            async with async_session_factory() as db:
                stats = await _fetch_broadcast_data(db)
                if active_connections:
                    await broadcast(stats)
        except Exception:
            pass
        await asyncio.sleep(5)


async def _fetch_broadcast_data(db: AsyncSession) -> dict:
    event_count = await db.scalar(select(func.count(Event.id)))
    active_count = await db.scalar(
        select(func.count(Event.id)).where(
            Event.status.in_(["IN_PROGRESS", "APPROVED"])
        )
    )
    client_count = await db.scalar(
        select(func.count(Client.id)).where(Client.is_active)
    )
    supplier_count = await db.scalar(
        select(func.count(Supplier.id)).where(Supplier.is_active)
    )
    total_revenue = await db.scalar(
        select(func.coalesce(func.sum(Event.total_revenue), 0))
    )
    total_cost = await db.scalar(select(func.coalesce(func.sum(Event.total_cost), 0)))
    rfq_count = await db.scalar(select(func.count(RFQ.id)).where(RFQ.status == "DRAFT"))

    recent = await db.execute(select(Event).order_by(Event.created_at.desc()).limit(10))
    recent_events = []
    for e in recent.scalars():
        client = await db.get(Client, e.client_id)
        recent_events.append(
            {
                "event_code": e.event_code,
                "status": e.status,
                "total_revenue": e.total_revenue,
                "client_name": client.name_en if client else "â€”",
            }
        )

    top = await db.execute(
        select(
            Client.name_en,
            func.count(Event.id).label("ec"),
            func.coalesce(func.sum(Event.total_revenue), 0).label("rev"),
        )
        .join(Event, Event.client_id == Client.id)
        .group_by(Client.id)
        .order_by(func.sum(Event.total_revenue).desc())
        .limit(5)
    )
    top_clients = [
        {"name_en": r.name_en, "event_count": r.ec, "total_revenue": round(r.rev, 2)}
        for r in top.all()
    ]

    eta_accepted = await db.scalar(
        select(func.count(EInvoiceRegister.id)).where(
            EInvoiceRegister.eta_status == "SUBMITTED"
        )
    )
    eta_rejected = await db.scalar(
        select(func.count(EInvoiceRegister.id)).where(
            EInvoiceRegister.eta_status == "REJECTED"
        )
    )
    total_eta = (eta_accepted or 0) + (eta_rejected or 0)
    eta_rate = (eta_accepted / total_eta * 100) if total_eta > 0 else 100.0

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "total_events": event_count or 0,
        "active_events": active_count or 0,
        "total_clients": client_count or 0,
        "total_suppliers": supplier_count or 0,
        "total_revenue_egp": round(total_revenue or 0, 2),
        "total_cost_egp": round(total_cost or 0, 2),
        "gross_profit": round((total_revenue or 0) - (total_cost or 0), 2),
        "avg_event_value": round((total_revenue or 0) / (event_count or 1), 2),
        "pending_rfqs": rfq_count or 0,
        "eta_success_rate": round(eta_rate, 2),
        "recent_events": recent_events,
        "top_clients": top_clients,
    }
