import httpx
import json
import base64
import hashlib
from datetime import datetime
from datetime import timezone, timedelta
from app.config import get_settings

settings = get_settings()

ETA_BASE_URL = settings.ETA_BASE_URL or "https://api.preprod.eta.gov.eg"
ETA_CLIENT_ID = settings.ETA_CLIENT_ID
ETA_CLIENT_SECRET = settings.ETA_CLIENT_SECRET


class ETAClient:
    _token: str | None = None
    _expires: datetime | None = None

    @staticmethod
    async def _get_token() -> str:
        if (
            ETAClient._token
            and ETAClient._expires
            and datetime.now(timezone.utc).replace(tzinfo=None) < ETAClient._expires
        ):
            return ETAClient._token

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{ETA_BASE_URL}/connect/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": ETA_CLIENT_ID,
                    "client_secret": ETA_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            ETAClient._token = data["access_token"]
            ETAClient._expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                seconds=data.get("expires_in", 3600) - 60
            )
            return ETAClient._token

    @staticmethod
    async def submit_documents(documents: list[dict]) -> dict:
        token = await ETAClient._get_token()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{ETA_BASE_URL}/api/v1.0/documentsubmissions",
                json={"documents": documents},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def get_document_status(uuid: str) -> dict:
        token = await ETAClient._get_token()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{ETA_BASE_URL}/api/v1.0/documents/{uuid}/raw",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def canonicalize_json(doc: dict) -> str:
        return json.dumps(
            doc, separators=(",", ":"), sort_keys=True, ensure_ascii=False, default=str
        )

    @staticmethod
    def compute_digest(canonical_json: str) -> str:
        sha256 = hashlib.sha256(canonical_json.encode("utf-8")).digest()
        return base64.b64encode(sha256).decode("utf-8")
