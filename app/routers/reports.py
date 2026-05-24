from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.auth import User
from app.services.report_engine import generate_executive_summary, render_executive_pdf

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
