import os
from pathlib import Path
from datetime import datetime

from app.celery_app import celery_app
from structlog import get_logger

logger = get_logger()
REPORT_DIR = Path(os.getenv("REPORT_OUTPUT_DIR", "/tmp/bio_erp_reports"))


@celery_app.task(bind=True)
def generate_excel_report(
    self, report_type: str, data: dict, filename: str | None = None
) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    name = filename or f"{report_type}_{ts}.xlsx"
    path = str(REPORT_DIR / name)

    from app.services.report_renderers import ExcelRenderer
    ExcelRenderer.generate(report_type, data, path)

    logger.info("report.excel.generated", path=path, type=report_type)
    return {"status": "completed", "path": path, "filename": name}


@celery_app.task(bind=True)
def generate_pdf_report(
    self, report_type: str, data: dict, template_name: str | None = None
) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    name = f"{report_type}_{ts}.pdf"
    path = str(REPORT_DIR / name)

    from app.services.report_renderers import PDFRenderer
    PDFRenderer.generate(report_type, data, path, template_name)

    logger.info("report.pdf.generated", path=path, type=report_type)
    return {"status": "completed", "path": path, "filename": name}
