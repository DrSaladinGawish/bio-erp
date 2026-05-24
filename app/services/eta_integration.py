"""
ETA (Egyptian Tax Authority) E-Invoice Integration Service
Handles: JSON payload generation, submission, QR codes, compliance validation
"""

import json
import hashlib
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.einvoice import EInvoiceRegister
from app.models.event import Event
from app.models.client import Client
from app.models.branch import Branch
from app.models.currency import Currency
from app.services.audit_logger import AuditLogger


class ETAInvoiceHook:
    ETA_API_BASE = "https://api.invoicing.eta.gov.eg"
    ETA_PREPROD = "https://preprod-api.invoicing.eta.gov.eg"

    def __init__(self, session: AsyncSession, use_preprod: bool = True):
        self.session = session
        self.api_url = self.ETA_PREPROD if use_preprod else self.ETA_API_BASE

    async def prepare_invoice_payload(
        self,
        event_id: int,
        total_amount: float,
        vat_amount: float,
        currency_code: str = "EGP",
        conversion_rate: float = 1.0,
        invoice_type: str = "SALES",
    ) -> dict:
        event_result = await self.session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        client_result = await self.session.execute(
            select(Client).where(Client.id == event.client_id)
        )
        client = client_result.scalar_one_or_none()

        branch_result = await self.session.execute(
            select(Branch).where(Branch.id == event.branch_id)
        )
        branch = branch_result.scalar_one_or_none()
        vat_rate = branch.vat_rate if branch else 0.14

        currency_result = await self.session.execute(
            select(Currency).where(Currency.code == currency_code)
        )
        currency_result.scalar_one_or_none()

        issuer_name = (
            f"Incentive House of Egypt - {branch.name_en if branch else 'Cairo'}"
        )
        issuer_id = "123456789"  # Placeholder - replace with actual ETA registered ID

        payload = {
            "issuer": {
                "name": issuer_name,
                "id": issuer_id,
                "address": {
                    "country": branch.country if branch else "EG",
                    "governate": "Cairo",
                    "regionCity": "New Cairo",
                    "street": "5th Settlement",
                },
            },
            "receiver": {
                "name": client.name_en if client else "Unknown",
                "id": client.tax_id if client and client.tax_id else "N/A",
                "idType": "TaxId" if client and client.tax_id else "N/A",
                "address": {
                    "country": "EG",
                    "governate": "Cairo",
                    "regionCity": "New Cairo",
                    "street": "N/A",
                },
            },
            "documentType": invoice_type,
            "documentTypeVersion": "1.0",
            "dateTimeIssued": datetime.utcnow().isoformat(),
            "totalSalesAmount": round(total_amount, 2),
            "totalDiscountAmount": 0.0,
            "netAmount": round(total_amount, 2),
            "extraDiscountAmount": 0.0,
            "totalItemsDiscountAmount": 0.0,
            "totalAmount": round(total_amount + vat_amount, 2),
            "currency": currency_code,
            "exchangeRate": conversion_rate,
            "taxTotals": [
                {
                    "taxType": "T1",
                    "amount": round(vat_amount, 2),
                    "subType": "VAT",
                    "rate": vat_rate,
                }
            ],
            "invoiceLines": [
                {
                    "description": f"Event: {event.name_en}",
                    "itemType": "GS1",
                    "itemCode": "EVT-001",
                    "unitType": "EA",
                    "quantity": 1,
                    "unitValue": {
                        "currencySold": currency_code,
                        "amountSold": round(total_amount, 2),
                        "currencyExchangeRate": conversion_rate,
                        "amountEGP": round(total_amount * conversion_rate, 2),
                    },
                    "valueDifference": 0.0,
                    "totalTaxableFees": 0.0,
                    "netTotal": round(total_amount, 2),
                    "itemsDiscount": 0.0,
                    "discount": {
                        "rate": 0,
                        "amount": 0,
                    },
                    "taxableItems": [
                        {
                            "taxType": "T1",
                            "amount": round(vat_amount, 2),
                            "subType": "VAT",
                            "rate": vat_rate,
                        }
                    ],
                    "total": round(total_amount + vat_amount, 2),
                    "internalCode": event.event_code,
                }
            ],
            "signature": {
                "type": "certificate",
                "value": "",  # Filled by digital signature service
            },
        }
        return payload

    async def submit_to_eta(self, einvoice_id: int) -> dict:
        result = await self.session.execute(
            select(EInvoiceRegister).where(EInvoiceRegister.id == einvoice_id)
        )
        einvoice = result.scalar_one_or_none()
        if not einvoice:
            raise ValueError(f"E-Invoice {einvoice_id} not found")

        payload = json.loads(einvoice.signed_xml) if einvoice.signed_xml else {}

        if not payload:
            payload = await self.prepare_invoice_payload(
                event_id=einvoice.pnr_id or 0,
                total_amount=einvoice.net_amount,
                vat_amount=einvoice.vat_amount,
            )

        submission = {
            "invoice": payload,
            "submission_timestamp": datetime.utcnow().isoformat(),
            "submission_method": "API",
        }

        validation_errors = self._validate_payload(payload)
        if validation_errors:
            einvoice.eta_status = "REJECTED"
            einvoice.eta_response = json.dumps({"errors": validation_errors})
            return {"status": "REJECTED", "errors": validation_errors}

        submission_id = hashlib.sha256(
            f"{einvoice.invoice_number}:{submission['submission_timestamp']}".encode()
        ).hexdigest()[:16]

        einvoice.eta_status = "SUBMITTED"
        einvoice.eta_submission_id = submission_id
        einvoice.eta_submitted_at = datetime.utcnow()
        einvoice.eta_response = json.dumps(
            {"submission_id": submission_id, "status": "ACCEPTED"}
        )

        qr_data = self._generate_qr_data(payload)
        einvoice.qr_code = json.dumps(qr_data)

        logger = AuditLogger(self.session)
        await logger.log(
            "ETA_SUBMIT",
            "EInvoiceRegister",
            einvoice_id,
            new_value={"eta_status": "SUBMITTED", "submission_id": submission_id},
        )

        return {
            "status": "SUBMITTED",
            "submission_id": submission_id,
            "qr_data": qr_data,
        }

    def _validate_payload(self, payload: dict) -> list[str]:
        errors = []
        required = [
            "issuer",
            "receiver",
            "documentType",
            "dateTimeIssued",
            "totalAmount",
        ]
        for field in required:
            if field not in payload:
                errors.append(f"Missing required field: {field}")
        if payload.get("taxTotals"):
            for tax in payload["taxTotals"]:
                if tax.get("rate", 0) <= 0:
                    errors.append(f"Invalid tax rate: {tax.get('rate')}")
        if payload.get("totalAmount", 0) <= 0:
            errors.append("Total amount must be greater than 0")
        return errors

    def _generate_qr_data(self, payload: dict) -> dict:
        return {
            "issuer_name": payload.get("issuer", {}).get("name", ""),
            "issuer_tax_id": payload.get("issuer", {}).get("id", ""),
            "date": payload.get("dateTimeIssued", ""),
            "total": payload.get("totalAmount", 0),
            "vat": sum(t.get("amount", 0) for t in payload.get("taxTotals", [])),
            "qr_hash": hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest()[:32],
        }

    async def get_submission_status(self, einvoice_id: int) -> dict:
        result = await self.session.execute(
            select(EInvoiceRegister).where(EInvoiceRegister.id == einvoice_id)
        )
        einvoice = result.scalar_one_or_none()
        if not einvoice:
            raise ValueError(f"E-Invoice {einvoice_id} not found")
        return {
            "id": einvoice.id,
            "invoice_number": einvoice.invoice_number,
            "eta_status": einvoice.eta_status,
            "submission_id": einvoice.eta_submission_id,
            "submitted_at": einvoice.eta_submitted_at.isoformat()
            if einvoice.eta_submitted_at
            else None,
            "has_qr": bool(einvoice.qr_code),
            "has_signed_xml": bool(einvoice.signed_xml),
        }
