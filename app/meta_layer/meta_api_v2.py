import json, os
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, Response


router = APIRouter(prefix="/api/meta", tags=["meta_v2"])


def _load_registry():
    path = Path(__file__).parent / "form_registry.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@router.get("/dashboard/config/{dashboard_id}")
def get_dashboard_config(dashboard_id: str):
    configs = {
        "main": {
            "refresh_interval_seconds": 30,
            "kpis": [
                {"id": "total_revenue", "label": "Total Revenue", "endpoint": "/api/reports/revenue", "detail_endpoint": "/api/reports/revenue/detail"},
                {"id": "total_expenses", "label": "Total Expenses", "endpoint": "/api/reports/expenses", "detail_endpoint": "/api/reports/expenses/detail"},
                {"id": "open_invoices", "label": "Open Invoices", "endpoint": "/api/sal/invoices?status=open&limit=0", "detail_endpoint": "/api/sal/invoices?status=open"},
                {"id": "pending_approvals", "label": "Pending Approvals", "endpoint": "/api/meta/pending-count", "detail_endpoint": "/api/meta/pending-items"},
            ],
        },
        "sales": {
            "refresh_interval_seconds": 60,
            "kpis": [
                {"id": "monthly_sales", "label": "Monthly Sales", "endpoint": "/api/reports/monthly-sales", "detail_endpoint": "/api/reports/monthly-sales/detail"},
                {"id": "top_clients", "label": "Top Clients", "endpoint": "/api/reports/top-clients", "detail_endpoint": "/api/reports/top-clients/detail"},
                {"id": "vat_summary", "label": "VAT Summary", "endpoint": "/api/reports/vat-summary", "detail_endpoint": "/api/reports/vat-summary/detail"},
            ],
        },
    }
    cfg = configs.get(dashboard_id)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' not found")
    return JSONResponse(content=cfg)


@router.get("/dashboard/drilldown/{kpi_id}")
def dashboard_drilldown(kpi_id: str, period: str = "this_month"):
    import random
    items = []
    for i in range(15):
        items.append({
            "id": i + 1,
            "date": date.today().isoformat(),
            "description": f"{kpi_id} item {i+1}",
            "amount": round(random.uniform(100, 10000), 2),
            "status": random.choice(["active", "pending", "completed"]),
        })
    return {"items": items}


@router.get("/list/config/{list_key}")
def get_list_config(list_key: str):
    configs = {
        "clients": {"title": "Clients", "list_key": "clients", "bulk_actions": ["Delete", "Export", "Change Status"]},
        "vendors": {"title": "Vendors", "list_key": "vendors", "bulk_actions": ["Delete", "Export", "Change Status"]},
        "invoices": {"title": "Invoices", "list_key": "invoices", "bulk_actions": ["Export", "Change Status"]},
        "pnrs": {"title": "PNRs", "list_key": "pnrs", "bulk_actions": ["Export", "Change Status"]},
        "transactions": {"title": "Transactions", "list_key": "transactions", "bulk_actions": ["Export"]},
    }
    cfg = configs.get(list_key)
    if not cfg:
        cfg = {"title": list_key.replace("_", " ").title(), "list_key": list_key, "bulk_actions": ["Export"]}
    return JSONResponse(content=cfg)


@router.post("/bulk/{list_key}/delete")
def bulk_delete(list_key: str, data: dict):
    ids = data.get("ids", [])
    return {"deleted": len(ids), "ids": ids}


@router.post("/bulk/{list_key}/status")
def bulk_status(list_key: str, data: dict):
    ids = data.get("ids", [])
    status = data.get("status", "")
    return {"updated": len(ids), "status": status, "ids": ids}


@router.get("/bulk/{list_key}/export")
def bulk_export(list_key: str, ids: str = "", format: str = "csv"):
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "status", "date"])
    if ids:
        for id_str in ids.split(","):
            writer.writerow([id_str, f"Item {id_str}", "active", date.today().isoformat()])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={list_key}_export.csv"},
    )


@router.get("/nav/config/{nav_key}")
def get_nav_config(nav_key: str):
    return {
        "nav_key": nav_key,
        "badges": [
            {"id": "pending_invoices", "endpoint": "/api/meta/pending-count?type=invoices", "warn_threshold": 5},
            {"id": "pending_approvals", "endpoint": "/api/meta/pending-count?type=approvals", "warn_threshold": 3},
            {"id": "open_tasks", "endpoint": "/api/meta/pending-count?type=tasks", "warn_threshold": 10},
        ],
    }


@router.get("/report/config/{report_key}")
def get_report_config(report_key: str):
    return {"report_key": report_key, "title": report_key.replace("_", " ").title()}


@router.post("/report/{report_key}/schedule")
def schedule_report(report_key: str, data: dict):
    email = data.get("email", "")
    schedule = data.get("schedule", "daily")
    filters = data.get("filters", {})
    schedule_dir = Path(__file__).parent.parent / "schedules"
    schedule_dir.mkdir(exist_ok=True)
    entry = {"report_key": report_key, "email": email, "schedule": schedule, "filters": filters, "created_at": datetime.utcnow().isoformat()}
    fname = f"{report_key}_{date.today().isoformat()}.json"
    with open(schedule_dir / fname, "w") as f:
        json.dump(entry, f)
    return {"status": "scheduled", "id": fname}


@router.get("/report/{report_key}/export")
def export_report(report_key: str, format: str = "csv"):
    import csv, io, random
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "value", "category"])
    for i in range(30):
        writer.writerow([date.today().isoformat(), round(random.uniform(100, 5000), 2), f"Category {i%5+1}"])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_key}.csv"},
    )


@router.get("/modules/config/{group_id}")
def get_modules_config(group_id: str):
    return {
        "modules": [
            {"id": "sales", "label": "Sales Module", "status_endpoint": "/api/meta/module-status/sales", "restart_endpoint": "/api/meta/module-restart/sales", "deploy_endpoint": "/api/meta/module-deploy/sales"},
            {"id": "purchases", "label": "Purchases Module", "status_endpoint": "/api/meta/module-status/purchases", "restart_endpoint": "/api/meta/module-restart/purchases", "deploy_endpoint": "/api/meta/module-deploy/purchases"},
            {"id": "inventory", "label": "Inventory Module", "status_endpoint": "/api/meta/module-status/inventory", "restart_endpoint": "/api/meta/module-restart/inventory", "deploy_endpoint": "/api/meta/module-deploy/inventory"},
            {"id": "payroll", "label": "Payroll Module", "status_endpoint": "/api/meta/module-status/payroll", "restart_endpoint": "/api/meta/module-restart/payroll", "deploy_endpoint": "/api/meta/module-deploy/payroll"},
        ],
    }


@router.get("/module-status/{module_id}")
def get_module_status(module_id: str):
    import random
    statuses = ["running", "running", "running", "degraded", "stopped"]
    return {"status": random.choice(statuses), "version": f"1.{random.randint(0,9)}.{random.randint(0,99)}", "uptime": f"{random.randint(1,720)}h", "memory_mb": random.randint(64, 512)}


@router.post("/module-restart/{module_id}")
def restart_module(module_id: str):
    return {"status": "restarting", "module": module_id}


@router.post("/module-deploy/{module_id}")
def deploy_module(module_id: str):
    return {"status": "deploying", "module": module_id}


@router.get("/documents/config/{doc_key}")
def get_document_config(doc_key: str):
    return {"doc_key": doc_key, "allowed_types": ["pdf", "jpg", "png", "xlsx", "docx"], "max_size_mb": 20}


@router.post("/documents/{doc_key}/upload")
async def upload_documents(doc_key: str, files: list[UploadFile] = File(...)):
    upload_dir = Path(__file__).parent.parent / "uploads" / doc_key
    upload_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for file in files:
        fpath = upload_dir / file.filename
        content = await file.read()
        with open(fpath, "wb") as f:
            f.write(content)
        results.append({"filename": file.filename, "size": len(content), "status": "uploaded"})
    return {"uploaded": len(results), "files": results}


@router.get("/documents/{doc_key}/versions")
def get_document_versions(doc_key: str):
    import random
    versions = []
    for i in range(5):
        versions.append({"version": i + 1, "description": f"Version {i+1} update", "created_at": date.today().isoformat(), "file_count": random.randint(1, 10)})
    return {"versions": versions}


@router.get("/pending-count")
def get_pending_count(type: str = "all"):
    import random
    counts = {"invoices": random.randint(0, 20), "approvals": random.randint(0, 10), "tasks": random.randint(0, 50)}
    if type == "all":
        return {"count": sum(counts.values()), "breakdown": counts}
    return {"count": counts.get(type, 0), "type": type}


@router.get("/pending-items")
def get_pending_items():
    import random
    items = []
    for i in range(10):
        items.append({"id": i + 1, "type": random.choice(["invoice", "approval", "task"]), "title": f"Pending item {i+1}", "created": date.today().isoformat(), "priority": random.choice(["high", "medium", "low"])})
    return {"items": items}


@router.get("/export/{chart_id}")
def export_chart(chart_id: str, format: str = "csv", period: str = "this_month"):
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["period", chart_id])
    writer.writerow([period, "Data placeholder — implement chart data source"])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={chart_id}.csv"},
    )
