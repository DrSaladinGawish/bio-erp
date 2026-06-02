from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.auth import User
from app.models import ReportMetadata
from app.schemas.report import ReportRequest, ReportResponse
from app.services.report_engine import generate_executive_summary, render_executive_pdf
from app.services.report_renderers import ExcelRenderer, PDFRenderer, CSVRenderer

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.post("/executive")
async def create_executive_report(
    period_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    summary = await generate_executive_summary(db, period_id)
    return summary


@router.get("/executive/{period_id}")
async def get_executive_report(
    period_id: int,
    format: str = Query("json"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    summary = await generate_executive_summary(db, period_id)
    if format == "pdf":
        pdf_bytes = await render_executive_pdf(summary)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=executive_summary_{period_id}.pdf",
            },
        )
    return summary


@router.get("/export")
async def export_report(
    format: str = Query(..., pattern="^(pdf|csv|json)$"),
    period_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    summary = await generate_executive_summary(db, period_id)
    if format == "pdf":
        pdf_bytes = await render_executive_pdf(summary)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=executive_report.pdf",
            },
        )
    if format == "csv":
        import csv
        import io

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["Cost Center", "Account", "Budgeted", "Actual", "Variance %", "Flag"]
        )
        for r in summary["variance_rows"]:
            writer.writerow(
                [
                    r["cost_center_name"],
                    r["coa_account_name"],
                    r["budgeted"],
                    r["actual"],
                    r["variance_pct"],
                    r["flag"],
                ]
            )
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=executive_report.csv",
            },
        )
    return summary


_REPORT_DIR = Path("/tmp/bio_erp_reports")
_RENDERER_MAP = {"xlsx": ExcelRenderer, "pdf": PDFRenderer, "csv": CSVRenderer}


async def _fetch_or_data(job_id: str, db: AsyncSession) -> Optional[dict]:
    result = await db.execute(
        text("SELECT data FROM or_jobs WHERE job_id = :jid"),
        {"jid": job_id},
    )
    row = result.fetchone()
    if row is None:
        return None
    return json.loads(row[0])


async def _store_report_metadata(
    filename: str, report_type: str, fmt: str, path: str, source_id: str | None, db: AsyncSession
) -> ReportResponse:
    meta = ReportMetadata(
        filename=filename,
        report_type=report_type,
        format=fmt,
        path=path,
        source_id=source_id,
    )
    db.add(meta)
    await db.commit()
    return ReportResponse(
        filename=filename,
        format=fmt,
        path=path,
        report_type=report_type,
        source_id=source_id,
    )


@router.post("/or-analysis/{job_id}")
async def export_or_analysis(
    job_id: str,
    fmt: str = Query(default="xlsx", pattern=r"^(xlsx|pdf|csv)$"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    data = await _fetch_or_data(job_id, db)
    if data is None:
        raise HTTPException(status_code=404, detail=f"OR job {job_id} not found")

    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"or_analysis_{job_id}_{ts}.{fmt}"
    path = str(_REPORT_DIR / filename)

    renderer = _RENDERER_MAP.get(fmt, ExcelRenderer)
    renderer.generate("or_analysis", data, path)

    report = await _store_report_metadata(filename, "or_analysis", fmt, path, job_id, db)
    return report


@router.post("/scm-cost")
async def export_scm_cost_report(
    req: ReportRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"scm_cost_{ts}.{req.format}"
    path = str(_REPORT_DIR / filename)

    data = req.data or {"source": "scm", "empty": False}
    renderer = _RENDERER_MAP.get(req.format, ExcelRenderer)
    renderer.generate("scm_cost", data, path)

    return await _store_report_metadata(filename, "scm_cost", req.format, path, req.source_id, db)


@router.post("/sustainability")
async def export_sustainability_report(
    req: ReportRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"sustainability_{ts}.{req.format}"
    path = str(_REPORT_DIR / filename)

    data = req.data or {"source": "sustainability", "empty": False}
    renderer = _RENDERER_MAP.get(req.format, PDFRenderer)
    renderer.generate("sustainability", data, path)

    return await _store_report_metadata(filename, "sustainability", req.format, path, req.source_id, db)
