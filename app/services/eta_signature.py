import base64
import hashlib
import json
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
from app.config import get_settings

settings = get_settings()


class ETASignatureService:
    PRIVATE_KEY_PATH = Path(
        getattr(settings, "ETA_PRIVATE_KEY_PATH", "./keys/eta_private.pem")
    )
    PUBLIC_KEY_PATH = Path(
        getattr(settings, "ETA_PUBLIC_KEY_PATH", "./keys/eta_public.pem")
    )

    @staticmethod
    def canonicalize(doc: dict) -> str:
        def strip_nulls(obj):
            if isinstance(obj, dict):
                return {
                    k: strip_nulls(v) for k, v in sorted(obj.items()) if v is not None
                }
            if isinstance(obj, list):
                return [strip_nulls(i) for i in obj if i is not None]
            return obj

        return json.dumps(strip_nulls(doc), separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def compute_digest(canonical_json: str) -> bytes:
        return hashlib.sha256(canonical_json.encode("utf-8")).digest()

    @classmethod
    def sign_document(cls, doc: dict) -> dict:
        canonical = cls.canonicalize(doc)
        digest = cls.compute_digest(canonical)

        if not cls.PRIVATE_KEY_PATH.exists():
            raise FileNotFoundError(
                f"ETA private key not found at {cls.PRIVATE_KEY_PATH}"
            )

        with open(cls.PRIVATE_KEY_PATH, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)

        signature = private_key.sign(
            digest,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        doc["signatures"] = [
            {
                "signatureType": "I",
                "value": base64.b64encode(signature).decode("utf-8"),
            }
        ]
        return doc

    @classmethod
    def verify_document(cls, doc: dict) -> bool:
        signatures = doc.pop("signatures", [])
        canonical = cls.canonicalize(doc)
        digest = cls.compute_digest(canonical)

        if not cls.PUBLIC_KEY_PATH.exists():
            return False

        with open(cls.PUBLIC_KEY_PATH, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())

        for sig in signatures:
            try:
                public_key.verify(
                    base64.b64decode(sig["value"]),
                    digest,
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
                return True
            except InvalidSignature:
                continue
        return False

    @classmethod
    def generate_keypair(cls, key_size: int = 3072):
        cls.PRIVATE_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        public_key = private_key.public_key()

        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pem_public = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        with open(cls.PRIVATE_KEY_PATH, "wb") as f:
            f.write(pem_private)
        with open(cls.PUBLIC_KEY_PATH, "wb") as f:
            f.write(pem_public)

        return {
            "private": str(cls.PRIVATE_KEY_PATH),
            "public": str(cls.PUBLIC_KEY_PATH),
            "fingerprint": hashlib.sha256(pem_public).hexdigest()[:16],
        }
