import json, os
from datetime import date, datetime
from pathlib import Path
from werkzeug.utils import secure_filename as _secure_filename

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse, FileResponse, Response

from app.middleware.auth import get_current_user

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".docx"}
MAX_UPLOAD_SIZE_MB = 20


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
    return {"items": [], "message": f"Drilldown for {kpi_id} not implemented yet"}


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
    return {"message": f"Export for {report_key} not implemented yet", "status": "not_implemented"}


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
    return {"status": "unknown", "message": f"Status check for {module_id} not implemented yet"}


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
async def upload_documents(
    doc_key: str,
    files: list[UploadFile] = File(...),
    _user=Depends(get_current_user),
):
    safe_doc_key = _secure_filename(doc_key)
    if not safe_doc_key or safe_doc_key != doc_key:
        raise HTTPException(status_code=400, detail="Invalid document key")

    base_upload_dir = Path(__file__).parent.parent / "uploads"
    base_upload_dir.mkdir(exist_ok=True)
    upload_dir = base_upload_dir / safe_doc_key
    upload_dir.mkdir(exist_ok=True)

    resolved_upload_dir = upload_dir.resolve()
    if not str(resolved_upload_dir).startswith(str(base_upload_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid upload path")

    results = []
    for file in files:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' not allowed. Allowed: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)}",
            )

        safe_name = _secure_filename(file.filename or "unnamed")
        if not safe_name:
            safe_name = f"file_{date.today().isoformat()}{ext}"

        fpath = upload_dir / safe_name
        if not fpath.resolve().startswith(resolved_upload_dir):
            raise HTTPException(status_code=400, detail="Invalid filename")

        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File exceeds {MAX_UPLOAD_SIZE_MB}MB limit")

        with open(fpath, "wb") as f:
            f.write(content)
        results.append({"filename": safe_name, "size": len(content), "status": "uploaded"})
    return {"uploaded": len(results), "files": results}


@router.get("/documents/{doc_key}/versions")
def get_document_versions(doc_key: str):
    return {"versions": [], "message": f"Document versions for {doc_key} not implemented yet"}


@router.get("/pending-count")
def get_pending_count(type: str = "all"):
    return {"count": 0, "message": "Pending count not implemented yet"}


@router.get("/pending-items")
def get_pending_items():
    return {"items": [], "message": "Pending items not implemented yet"}


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
