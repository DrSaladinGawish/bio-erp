import asyncio
import httpx
from datetime import datetime
from datetime import timezone
from typing import Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from app.config import get_settings
from app.services.eta_client import ETAClient
from app.services.eta_signature import ETASignatureService

settings = get_settings()

ETA_PROD_URL = getattr(settings, "ETA_BASE_URL", "https://api.eta.gov.eg")
ETA_MAX_BATCH = 100

ETA_ERROR_CODES = {
    "T1": "Taxpayer not registered or inactive",
    "T2": "Invalid digital signature",
    "T3": "Invalid document structure or schema violation",
    "T4": "Duplicate internal ID",
    "T5": "Invalid issuer or receiver data",
    "T6": "Invalid item code (GS1/EGS/HS)",
    "T7": "Tax calculation mismatch",
    "T8": "Invalid date or future-dated invoice",
    "T9": "Invalid taxpayer activity code",
    "T10": "Invalid address format",
    "T11": "Receiver VAT ID invalid",
    "T12": "Total amount mismatch",
    "T13": "Currency code not supported",
    "T14": "Discount exceeds line total",
    "T15": "Missing required field",
    "T16": "Unauthorized document type for taxpayer",
    "T17": "Invoice exceeds maximum line items (200)",
    "T18": "Batch size exceeds limit (100)",
    "T19": "Rate limit exceeded â€” retry after 60s",
    "T20": "Service temporarily unavailable",
}


class ETAProductionError(Exception):
    def __init__(self, code: str, message: str, details: Optional[dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class ETAProductionClient:
    @staticmethod
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(
            (httpx.HTTPStatusError, httpx.NetworkError, httpx.TimeoutException)
        ),
        reraise=True,
    )
    async def _post_with_retry(
        url: str, json_payload: dict, headers: dict
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=json_payload, headers=headers)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                await asyncio.sleep(retry_after)
                resp.raise_for_status()
            if resp.status_code >= 500:
                resp.raise_for_status()
            return resp

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.NetworkError)),
        reraise=True,
    )
    async def _get_with_retry(url: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code >= 500:
                resp.raise_for_status()
            return resp

    @classmethod
    async def submit_batch(cls, documents: list[dict]) -> dict:
        if len(documents) > ETA_MAX_BATCH:
            raise ETAProductionError(
                "T18", f"Batch size {len(documents)} exceeds limit of {ETA_MAX_BATCH}"
            )

        signed_docs = []
        for doc in documents:
            try:
                signed = ETASignatureService.sign_document(doc)
                signed_docs.append(signed)
            except FileNotFoundError:
                raise ETAProductionError(
                    "T2", "Digital signature key missing â€” cannot submit to production"
                )

        token = await ETAClient._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": f"batch-{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d%H%M%S')}-{len(signed_docs)}",
        }

        try:
            resp = await cls._post_with_retry(
                f"{ETA_PROD_URL}/api/v1.0/documentsubmissions",
                {"documents": signed_docs},
                headers,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                error_body = e.response.json()
                error_code = error_body.get("error", {}).get("code", "T3")
                raise ETAProductionError(
                    error_code,
                    ETA_ERROR_CODES.get(error_code, "Unknown validation error"),
                    error_body,
                )
            raise ETAProductionError(
                "T20", f"HTTP {e.response.status_code}: {e.response.text}"
            )

        result = resp.json()
        accepted = result.get("acceptedDocuments", [])
        rejected = result.get("rejectedDocuments", [])

        enriched_rejected = []
        for rej in rejected:
            error_details = rej.get("error", {})
            code = error_details.get("code", "T3")
            enriched_rejected.append(
                {
                    "uuid": rej.get("uuid"),
                    "internalId": rej.get("internalId"),
                    "code": code,
                    "reason": ETA_ERROR_CODES.get(
                        code, error_details.get("message", "Unknown error")
                    ),
                    "details": error_details.get("target", ""),
                    "retryable": code in {"T19", "T20", "T4"},
                }
            )

        return {
            "submissionId": result.get("submissionId"),
            "documentCount": result.get("documentCount"),
            "accepted": accepted,
            "rejected": enriched_rejected,
            "batch_size": len(signed_docs),
        }

    @classmethod
    async def get_document_status(cls, uuid: str) -> dict:
        token = await ETAClient._get_token()
        headers = {"Authorization": f"Bearer {token}"}

        try:
            resp = await cls._get_with_retry(
                f"{ETA_PROD_URL}/api/v1.0/documents/{uuid}/raw",
                headers,
            )
            data = resp.json()
            return {
                "uuid": data.get("uuid"),
                "longId": data.get("longId"),
                "internalId": data.get("internalId"),
                "status": data.get("status"),
                "rejectionReason": data.get("rejectionReason"),
                "dateTimeIssued": data.get("dateTimeIssued"),
                "totalAmount": data.get("totalAmount"),
                "taxTotals": data.get("taxTotals"),
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "uuid": uuid,
                    "status": "NotFound",
                    "rejectionReason": "Document not yet available or invalid UUID",
                }
            raise ETAProductionError(
                "T20", f"Status check failed: HTTP {e.response.status_code}"
            )

    @classmethod
    async def poll_until_valid(
        cls, uuid: str, max_attempts: int = 10, interval: int = 5
    ) -> dict:
        for attempt in range(max_attempts):
            status = await cls.get_document_status(uuid)
            current = status.get("status", "")
            if current in {"Valid", "Invalid", "Rejected"}:
                return {**status, "poll_attempts": attempt + 1, "resolved": True}
            await asyncio.sleep(interval)
        return {
            **status,
            "poll_attempts": max_attempts,
            "resolved": False,
            "note": "Polling timeout â€” check manually",
        }
