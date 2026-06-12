from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Optional
from xml.dom import minidom

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models_production import SalesInvoice, SalesLineItem, Client, Vendor


def _prettify(elem: ET.Element) -> str:
    rough = ET.tostring(elem, encoding="unicode")
    reparsed = minidom.parseString(rough.encode())
    return reparsed.toprettyxml(indent="  ")


async def generate_invoice_xml(
    session: AsyncSession,
    invoice_id: int,
) -> dict:
    result = await session.execute(
        select(SalesInvoice).where(SalesInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        return {"error": f"Sales invoice {invoice_id} not found"}

    client = None
    if invoice.client_id:
        result = await session.execute(
            select(Client).where(Client.id == invoice.client_id)
        )
        client = result.scalar_one_or_none()

    result = await session.execute(
        select(SalesLineItem)
        .where(SalesLineItem.invoice_id == invoice_id)
        .order_by(SalesLineItem.line_no)
    )
    lines = result.scalars().all()

    root = ET.Element("Invoice")
    root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    header = ET.SubElement(root, "InvoiceHeader")
    ET.SubElement(header, "InvoiceNumber").text = invoice.invoice_no or str(invoice.id)
    ET.SubElement(header, "InvoiceDate").text = invoice.invoice_date.isoformat() if invoice.invoice_date else ""
    ET.SubElement(header, "InvoiceType").text = "SALES"
    ET.SubElement(header, "Currency").text = invoice.currency or "EGP"
    ET.SubElement(header, "ExchangeRate").text = str(invoice.exchange_rate or 1.0)

    issuer = ET.SubElement(header, "Issuer")
    ET.SubElement(issuer, "Name").text = "Incentive House of Egypt"
    ET.SubElement(issuer, "TaxID").text = ""
    ET.SubElement(issuer, "Type").text = "B"

    receiver = ET.SubElement(header, "Receiver")
    if client:
        ET.SubElement(receiver, "Name").text = client.name or ""
        ET.SubElement(receiver, "TaxID").text = client.tax_id or ""
    else:
        ET.SubElement(receiver, "Name").text = "Walk-in Customer"
        ET.SubElement(receiver, "TaxID").text = ""

    line_items = ET.SubElement(root, "InvoiceLines")
    for i, line in enumerate(lines):
        li = ET.SubElement(line_items, "LineItem")
        ET.SubElement(li, "LineNumber").text = str(i + 1)
        ET.SubElement(li, "ItemCode").text = line.item_code or ""
        ET.SubElement(li, "Description").text = line.description or ""
        ET.SubElement(li, "Quantity").text = str(line.quantity or 1.0)
        ET.SubElement(li, "UnitPrice").text = str(line.unit_price or 0.0)
        ET.SubElement(li, "Discount").text = str(line.discount or 0.0)
        ET.SubElement(li, "TaxRate").text = str(line.tax_rate or 0.0)
        line_total = (line.quantity or 0) * (line.unit_price or 0) - (line.discount or 0)
        ET.SubElement(li, "LineTotal").text = str(round(line_total, 2))
        tax_amount = line_total * (line.tax_rate or 0)
        ET.SubElement(li, "TaxAmount").text = str(round(tax_amount, 2))

    totals = ET.SubElement(root, "InvoiceTotals")
    ET.SubElement(totals, "NetTotal").text = str(round(invoice.subtotal or 0, 2))
    ET.SubElement(totals, "TaxTotal").text = str(round(invoice.tax_amount or 0, 2))
    ET.SubElement(totals, "GrossTotal").text = str(round(invoice.total or 0, 2))
    ET.SubElement(totals, "PaidAmount").text = str(round(invoice.paid_amount or 0, 2))
    ET.SubElement(totals, "AmountDue").text = str(round((invoice.total or 0) - (invoice.paid_amount or 0), 2))

    ext = ET.SubElement(root, "Signatures")
    ET.SubElement(ext, "Signature").text = "PLACEHOLDER_SIGNATURE"
    ET.SubElement(ext, "QRCode").text = "PLACEHOLDER_QR"

    xml_str = _prettify(root)
    return {
        "invoice_id": invoice.id,
        "invoice_no": invoice.invoice_no,
        "xml": xml_str,
        "line_count": len(lines),
        "total": round(invoice.total or 0, 2),
        "generated_at": datetime.now().isoformat(),
    }


async def generate_bulk_xml(
    session: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    stmt = select(SalesInvoice).order_by(SalesInvoice.invoice_date)
    filters = []
    if date_from:
        filters.append(SalesInvoice.invoice_date >= date_from)
    if date_to:
        filters.append(SalesInvoice.invoice_date <= date_to)
    if filters:
        stmt = stmt.where(*filters)
    result = await session.execute(stmt)
    invoices = result.scalars().all()
    results = []
    for inv in invoices:
        res = await generate_invoice_xml(session, inv.id)
        results.append(res)
    return results
