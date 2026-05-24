import asyncio
import json
from datetime import datetime
from datetime import timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.middleware.auth import get_current_user, RequirePermission
from app.models import User, Event, EventLineItem, ETASubmissionQueue
from app.services.eta_production import ETAProductionClient, ETAProductionError
from app.services.email_service import EmailService
from app.services.audit_logger import log_action
from app.config import get_settings

settings = get_settings()
router = APIRouter(tags=["ETA Compliance"])


def build_eta_invoice(
    event: Event,
    client,
    line_items: list[EventLineItem],
    issuer_id: str,
    issuer_name: str,
    activity_code: str = "6201",
) -> dict:
    eta_lines = []
    total_sales = Decimal("0.00")
    total_net = Decimal("0.00")
    total_tax = Decimal("0.00")

    for li in line_items:
        item = li.item
        qty = Decimal(str(li.quantity)) if li.quantity else Decimal("1.00")
        unit_price = Decimal(str(li.unit_cost)) if li.unit_cost else Decimal("0.00")
        line_total = qty * unit_price
        vat_amount = line_total * Decimal("0.14")
        net_total = line_total + vat_amount

        total_sales += line_total
        total_net += net_total
        total_tax += vat_amount

        eta_lines.append(
            {
                "description": item.name_en if item else (li.description or "Service"),
                "itemType": "EGS",
                "itemCode": str(item.id) if item else "0000",
                "unitType": "EA",
                "quantity": qty,
                "internalCode": str(item.id) if item else None,
                "salesTotal": round(line_total, 5),
                "total": round(net_total, 5),
                "valueDiscount": Decimal("0.00"),
                "discount": {"currencySold": "EGP", "amountEGP": Decimal("0.00")},
                "taxableItems": [
                    {
                        "taxType": "T1",
                        "amount": round(vat_amount, 5),
                        "subType": "V009",
                        "rate": Decimal("14.00"),
                    }
                ],
                "netTotal": round(net_total, 5),
                "itemsDiscount": Decimal("0.00"),
            }
        )

    document = {
        "issuer": {
            "type": "B",
            "id": issuer_id,
            "name": issuer_name,
            "address": {
                "country": "EG",
                "governate": "Cairo",
                "regionCity": "Nasr City",
                "street": "Tahrir St",
                "buildingNumber": "1",
            },
        },
        "receiver": {
            "type": "B" if (client and client.tax_id) else "P",
            "id": client.tax_id if client else "000000000",
            "name": client.name_en if client else "Unknown",
            "address": {
                "country": "EG",
                "governate": client.address_en.split(",")[0].strip()
                if client and client.address_en
                else "Cairo",
                "regionCity": client.address_en.split(",")[0].strip()
                if client and client.address_en
                else "Cairo",
                "street": client.address_en if client else "Main St",
                "buildingNumber": "1",
            },
        }
        if client
        else None,
        "documentType": "I",
        "documentTypeVersion": "1.0",
        "dateTimeIssued": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "taxpayerActivityCode": activity_code,
        "internalID": f"INV-{event.id}-{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d%H%M%S')}",
        "totalDiscountAmount": Decimal("0.00"),
        "totalSalesAmount": round(total_sales, 5),
        "netAmount": round(total_sales, 5),
        "taxTotals": [
            {
                "taxType": "T1",
                "amount": round(total_tax, 5),
                "subType": "V009",
                "rate": Decimal("14.00"),
            }
        ],
        "totalAmount": round(total_net, 5),
        "extraDiscountAmount": Decimal("0.00"),
        "totalItemsDiscountAmount": Decimal("0.00"),
        "invoiceLines": eta_lines,
    }

    def clean_nulls(d):
        if isinstance(d, dict):
            return {k: clean_nulls(v) for k, v in d.items() if v is not None}
        elif isinstance(d, list):
            return [clean_nulls(i) for i in d]
        return d

    return clean_nulls(document)


@router.post("/submit/{event_id}", response_model=dict)
async def submit_single_event(
    event_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("invoice_create")),
):
    result = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(
            joinedload(Event.client),
            joinedload(Event.line_items).joinedload(EventLineItem.item),
        )
    )
    event = result.unique().scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event.client:
        raise HTTPException(status_code=400, detail="Event has no client assigned")

    issuer_id = getattr(settings, "COMPANY_TAX_ID", "123456789")
    issuer_name = getattr(settings, "COMPANY_NAME", "BIO-ERP Company")

    doc = build_eta_invoice(
        event, event.client, event.line_items, issuer_id, issuer_name
    )
    internal_id = doc["internalID"]

    dup_check = await db.execute(
        select(ETASubmissionQueue).where(ETASubmissionQueue.internal_id == internal_id)
    )
    if dup_check.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail=f"Invoice {internal_id} already submitted or queued"
        )

    try:
        result = await ETAProductionClient.submit_batch([doc])
    except ETAProductionError as e:
        if e.code in {"T19", "T20", "T4"}:
            queue = ETASubmissionQueue(
                event_id=event_id,
                internal_id=internal_id,
                document_json=json.dumps(doc),
                status="retrying",
                retry_count=1,
                last_error=f"[{e.code}] {e.message}",
            )
            db.add(queue)
            await db.commit()
            raise HTTPException(
                status_code=202,
                detail={
                    "message": "Submission queued for retry",
                    "error_code": e.code,
                    "reason": e.message,
                    "queue_id": queue.id,
                },
            )
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": e.code,
                "reason": e.message,
                "details": e.details,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    accepted = result.get("accepted", [])
    rejected = result.get("rejected", [])

    if accepted:
        acc = accepted[0]
        queue = ETASubmissionQueue(
            event_id=event_id,
            internal_id=internal_id,
            document_json=json.dumps(doc),
            status="accepted",
            eta_uuid=acc.get("uuid"),
            eta_long_id=acc.get("longId"),
            submission_id=result.get("submissionId"),
            submitted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            resolved_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(queue)
        background_tasks.add_task(poll_and_notify, acc.get("uuid"), user.email)

    if rejected:
        rej = rejected[0]
        queue = ETASubmissionQueue(
            event_id=event_id,
            internal_id=internal_id,
            document_json=json.dumps(doc),
            status="rejected",
            rejection_code=rej.get("code"),
            rejection_reason=rej.get("reason"),
            submitted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(queue)
        background_tasks.add_task(
            EmailService.eta_alert,
            recipient=user.email,
            invoice_uuid=internal_id,
            status="REJECTED",
            errors=[f"{rej['code']}: {rej['reason']}"],
        )

    await log_action(
        db=db,
        user=user,
        action="ETA_SUBMIT",
        entity_type="event",
        entity_id=event_id,
        new_value={
            "submission_id": result.get("submissionId"),
            "internal_id": internal_id,
            "accepted": len(accepted),
            "rejected": len(rejected),
        },
    )
    await db.commit()

    return {
        "submission_id": result.get("submissionId"),
        "internal_id": internal_id,
        "accepted": accepted,
        "rejected": rejected,
        "status": "accepted" if accepted else "rejected",
    }


@router.post("/submit-batch", response_model=dict)
async def submit_batch_events(
    event_ids: list[int],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("invoice_create")),
):
    if len(event_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 events per batch")

    result = await db.execute(
        select(Event)
        .where(Event.id.in_(event_ids))
        .options(
            joinedload(Event.client),
            joinedload(Event.line_items).joinedload(EventLineItem.item),
        )
    )
    events = result.unique().scalars().all()

    if len(events) != len(event_ids):
        found = {e.id for e in events}
        missing = set(event_ids) - found
        raise HTTPException(status_code=404, detail=f"Events not found: {missing}")

    issuer_id = getattr(settings, "COMPANY_TAX_ID", "123456789")
    issuer_name = getattr(settings, "COMPANY_NAME", "BIO-ERP Company")

    docs = []
    for event in events:
        if not event.client:
            raise HTTPException(
                status_code=400, detail=f"Event {event.id} has no client"
            )
        doc = build_eta_invoice(
            event, event.client, event.line_items, issuer_id, issuer_name
        )
        docs.append(doc)

    try:
        result = await ETAProductionClient.submit_batch(docs)
    except ETAProductionError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": e.code,
                "reason": e.message,
                "details": e.details,
            },
        )

    for i, acc in enumerate(result.get("accepted", [])):
        queue = ETASubmissionQueue(
            event_id=event_ids[i],
            internal_id=docs[i]["internalID"],
            document_json=json.dumps(docs[i]),
            status="accepted",
            eta_uuid=acc.get("uuid"),
            eta_long_id=acc.get("longId"),
            submission_id=result.get("submissionId"),
            submitted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            resolved_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(queue)
        background_tasks.add_task(poll_and_notify, acc.get("uuid"), user.email)

    for rej in result.get("rejected", []):
        idx = next(
            (i for i, d in enumerate(docs) if d["internalID"] == rej.get("internalId")),
            0,
        )
        queue = ETASubmissionQueue(
            event_id=event_ids[idx],
            internal_id=rej.get("internalId"),
            document_json=json.dumps(docs[idx]),
            status="rejected",
            rejection_code=rej.get("code"),
            rejection_reason=rej.get("reason"),
            submitted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(queue)

    await db.commit()

    return {
        "submission_id": result.get("submissionId"),
        "batch_size": len(docs),
        "accepted_count": len(result.get("accepted", [])),
        "rejected_count": len(result.get("rejected", [])),
        "accepted": result.get("accepted", []),
        "rejected": result.get("rejected", []),
    }


@router.get("/status/{document_uuid}", response_model=dict)
async def get_production_status(
    document_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        status = await ETAProductionClient.get_document_status(document_uuid)
    except ETAProductionError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error_code": e.code,
                "reason": e.message,
            },
        )

    result = await db.execute(
        select(ETASubmissionQueue).where(ETASubmissionQueue.eta_uuid == document_uuid)
    )
    queue = result.scalar_one_or_none()
    if queue and status.get("status") in {"Valid", "Invalid", "Rejected"}:
        queue.status = status["status"].lower()
        queue.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if status.get("rejectionReason"):
            queue.rejection_reason = status["rejectionReason"]
        await db.commit()

    return status


@router.get("/queue", response_model=list)
async def list_queue(
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("invoice_view")),
):
    query = select(ETASubmissionQueue).order_by(ETASubmissionQueue.created_at.desc())
    if status_filter:
        query = query.where(ETASubmissionQueue.status == status_filter)
    result = await db.execute(query.limit(100))
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "event_id": r.event_id,
            "internal_id": r.internal_id,
            "status": r.status,
            "retry_count": r.retry_count,
            "eta_uuid": r.eta_uuid,
            "eta_long_id": r.eta_long_id,
            "rejection_code": r.rejection_code,
            "rejection_reason": r.rejection_reason,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        }
        for r in rows
    ]


async def poll_and_notify(uuid: str, recipient_email: str):
    await asyncio.sleep(10)
    try:
        status = await ETAProductionClient.poll_until_valid(
            uuid, max_attempts=12, interval=10
        )
        if status.get("resolved"):
            await EmailService.eta_alert(
                recipient=recipient_email,
                invoice_uuid=uuid,
                status=status["status"],
            )
    except Exception as e:
        print(f"[Poll Notify] Failed for {uuid}: {e}")
