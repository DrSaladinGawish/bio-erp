from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user, RequirePermission
from app.models.auth import User
from app.services.cbe_sync import trigger_manual_sync
from app.services.email_service import EmailService
from app.services.pdf_service import PDFService
import os

router = APIRouter()


@router.post("/cbe-sync/trigger")
async def manual_cbe_sync(user: User = Depends(RequirePermission("currency_edit"))):
    await trigger_manual_sync()
    return {"status": "ok", "message": "CBE sync triggered manually"}


@router.post("/email/test")
async def test_email(
    recipient: str,
    user: User = Depends(get_current_user),
):
    success = await EmailService.send(
        to=[recipient],
        subject="BIO-ERP Email Test",
        body_html="<h2>SMTP is working</h2><p>BIO-ERP notification service online.</p>",
    )
    return {"sent": success}


@router.post("/pdf/invoice-test")
async def test_invoice_pdf():
    data = {
        "invoice_no": "INV-TEST-001",
        "date": "2026-05-17",
        "client_name": "\u0634\u0631\u0643\u0629 \u0627\u0644\u0646\u064a\u0644 \u0644\u0644\u0641\u0639\u0627\u0644\u064a\u0627\u062a",
        "client_vat": "123456789",
        "branch": "\u0627\u0644\u0642\u0627\u0647\u0631\u0629",
        "currency": "EGP",
        "vat_rate": 14,
        "items": [
            {
                "description": "\u062e\u062f\u0645\u0627\u062a \u0625\u0646\u062a\u0627\u062c \u0641\u0639\u0627\u0644\u064a\u0629",
                "qty": 1,
                "unit_price": 50000.0,
                "total": 50000.0,
            }
        ],
        "subtotal": 50000.0,
        "vat_amount": 7000.0,
        "total": 57000.0,
    }
    os.makedirs("uploads/invoices", exist_ok=True)
    pdf_bytes = PDFService.generate_invoice(
        data, output_path="uploads/invoices/test_invoice.pdf"
    )
    return {
        "generated": True,
        "path": "uploads/invoices/test_invoice.pdf",
        "size_bytes": len(pdf_bytes),
    }
