"""
P0-A3: Automated Backup & Disaster Recovery Service
Zero Gap Compliance — Daily PostgreSQL dumps, encrypted, checksum-verified.
"""

import os
import gzip
import shutil
import subprocess
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from cryptography.fernet import Fernet

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "D:/ERP System/BIO_ERP/backups"))
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "bio_erp")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres123")
ENCRYPTION_KEY = os.getenv("BACKUP_ENCRYPTION_KEY")
CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "local")


def get_fernet() -> Fernet:
    """Get or create persistent Fernet key. Key survives restarts."""
    env_key = os.getenv("FERNET_KEY")
    if env_key:
        try:
            return Fernet(env_key.encode())
        except Exception:
            pass
    key_file = Path(os.path.dirname(__file__), ".fernet_key")
    if key_file.exists():
        try:
            return Fernet(key_file.read_bytes().strip())
        except Exception:
            pass
    new_key = Fernet.generate_key()
    key_file.write_bytes(new_key)
    try:
        os.chmod(str(key_file), 0o600)
    except OSError:
        pass
    print(f"[BACKUP] New Fernet key saved to {key_file}")
    print(f"[BACKUP] For production, set env var: FERNET_KEY={new_key.decode()}")
    return Fernet(new_key)


class BackupRecord:
    def __init__(
        self,
        filename: str,
        size_bytes: int,
        checksum: str,
        started_at: datetime,
        completed_at: datetime,
        tables_backed: int,
        status: str,
        error: str = None,
    ):
        self.filename = filename
        self.size_bytes = size_bytes
        self.checksum = checksum
        self.started_at = started_at
        self.completed_at = completed_at
        self.tables_backed = tables_backed
        self.status = status
        self.error = error

    def to_dict(self):
        return {
            "filename": self.filename,
            "size_mb": round(self.size_bytes / 1024 / 1024, 2),
            "checksum": self.checksum,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_sec": (self.completed_at - self.started_at).total_seconds(),
            "tables_backed": self.tables_backed,
            "status": self.status,
        }


class BackupService:
    def __init__(self):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self.records: List[BackupRecord] = []

    def create_backup(self, backup_type: str = "full") -> BackupRecord:
        started = datetime.now()
        timestamp = started.strftime("%Y%m%d_%H%M%S")
        filename = f"bio_erp_{backup_type}_{timestamp}.sql"
        filepath = BACKUP_DIR / filename
        compressed_path = Path(str(filepath) + ".gz")

        try:
            env = os.environ.copy()
            env["PGPASSWORD"] = PG_PASSWORD
            cmd = [
                "pg_dump",
                "-h",
                PG_HOST,
                "-p",
                PG_PORT,
                "-U",
                PG_USER,
                "-d",
                PG_DB,
                "-f",
                str(filepath),
                "--verbose",
            ]
            if backup_type == "schema_only":
                cmd.append("--schema-only")
            elif backup_type == "data_only":
                cmd.append("--data-only")
            elif backup_type == "custom":
                cmd.extend(["-Fc", "-f", str(filepath).replace(".sql", ".dump")])

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"pg_dump failed: {result.stderr}")

            tables_backed = self._count_tables_in_dump(filepath)
            self._compress_file(filepath, compressed_path)
            final_path = compressed_path

            if ENCRYPTION_KEY:
                encrypted_path = self._encrypt_file(compressed_path)
                final_path = encrypted_path

            checksum = self._calculate_checksum(final_path)
            if CLOUD_PROVIDER != "local":
                self._upload_to_cloud(final_path)

            if filepath.exists():
                filepath.unlink()

            completed = datetime.now()
            record = BackupRecord(
                final_path.name,
                final_path.stat().st_size,
                checksum,
                started,
                completed,
                tables_backed,
                "success",
            )
            self._save_record(record)
            return record

        except Exception as e:
            completed = datetime.now()
            record = BackupRecord(
                compressed_path.name if compressed_path.exists() else filename,
                0,
                "",
                started,
                completed,
                0,
                "failed",
                str(e),
            )
            self._save_record(record)
            raise

    def restore_backup(
        self, filename: str, target_db: str = None, verify_only: bool = False
    ) -> dict:
        filepath = BACKUP_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Backup not found: {filepath}")
        with open(BACKUP_DIR / f"{filename}.json") as f:
            metadata = json.load(f)
        actual_checksum = self._calculate_checksum(filepath)
        if actual_checksum != metadata["checksum"]:
            raise ValueError("Checksum mismatch!")
        if verify_only:
            return {"verified": True, "filename": filename}

        if filename.endswith(".enc"):
            filepath = self._decrypt_file(filepath)
        if str(filepath).endswith(".gz"):
            decompressed = Path(str(filepath).replace(".gz", ""))
            self._decompress_file(filepath, decompressed)
            filepath = decompressed

        env = os.environ.copy()
        env["PGPASSWORD"] = PG_PASSWORD
        target = target_db or PG_DB
        cmd = [
            "psql",
            "-h",
            PG_HOST,
            "-p",
            PG_PORT,
            "-U",
            PG_USER,
            "-d",
            target,
            "-f",
            str(filepath),
        ]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        return {
            "restored": result.returncode == 0,
            "filename": filename,
            "target_db": target,
        }

    def list_backups(self) -> List[dict]:
        backups = []
        for meta_file in BACKUP_DIR.glob("*.json"):
            with open(meta_file) as f:
                backups.append(json.load(f))
        return sorted(backups, key=lambda x: x["started_at"], reverse=True)

    def cleanup_old_backups(self) -> dict:
        cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
        removed = 0
        for meta_file in BACKUP_DIR.glob("*.json"):
            with open(meta_file) as f:
                data = json.load(f)
            started = datetime.fromisoformat(data["started_at"])
            if started < cutoff:
                backup_file = BACKUP_DIR / data["filename"]
                if backup_file.exists():
                    backup_file.unlink()
                meta_file.unlink()
                removed += 1
        return {"removed": removed, "retention_days": RETENTION_DAYS}

    def verify_all_backups(self) -> List[dict]:
        results = []
        for meta_file in BACKUP_DIR.glob("*.json"):
            with open(meta_file) as f:
                data = json.load(f)
            filepath = BACKUP_DIR / data["filename"]
            if not filepath.exists():
                results.append(
                    {
                        "filename": data["filename"],
                        "verified": False,
                        "error": "File missing",
                    }
                )
                continue
            actual = self._calculate_checksum(filepath)
            results.append(
                {"filename": data["filename"], "verified": actual == data["checksum"]}
            )
        return results

    def _count_tables_in_dump(self, filepath: Path) -> int:
        count = 0
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "CREATE TABLE" in line:
                    count += 1
        return count

    def _compress_file(self, source: Path, dest: Path):
        with open(source, "rb") as f_in:
            with gzip.open(dest, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

    def _decompress_file(self, source: Path, dest: Path):
        with gzip.open(source, "rb") as f_in:
            with open(dest, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

    def _encrypt_file(self, filepath: Path) -> Path:
        f = get_fernet()
        out_path = Path(str(filepath) + ".enc")
        with open(filepath, "rb") as f_in:
            data = f_in.read()
        encrypted = f.encrypt(data)
        with open(out_path, "wb") as f_out:
            f_out.write(encrypted)
        filepath.unlink()
        return out_path

    def _decrypt_file(self, filepath: Path) -> Path:
        f = get_fernet()
        out_path = Path(str(filepath).replace(".enc", ""))
        with open(filepath, "rb") as f_in:
            data = f_in.read()
        decrypted = f.decrypt(data)
        with open(out_path, "wb") as f_out:
            f_out.write(decrypted)
        filepath.unlink()
        return out_path

    def _calculate_checksum(self, filepath: Path) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _upload_to_cloud(self, filepath: Path):
        if CLOUD_PROVIDER == "s3":
            import boto3

            s3 = boto3.client("s3")
            bucket = os.getenv("S3_BUCKET", "bio-erp-backups")
            s3.upload_file(str(filepath), bucket, f"backups/{filepath.name}")

    def _save_record(self, record: BackupRecord):
        meta_path = BACKUP_DIR / f"{record.filename}.json"
        with open(meta_path, "w") as f:
            json.dump(record.to_dict(), f, indent=2, default=str)


# ── API Router ──

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel

from app.organs.incentivehouse_organ.rbac import Permission, require_permission

router = APIRouter(prefix="/backup", tags=["Backup & DR"])


class BackupRequest(BaseModel):
    backup_type: str = "full"


class RestoreRequest(BaseModel):
    filename: str
    target_db: Optional[str] = None
    verify_only: bool = False


@router.post("/create")
def create_backup(
    req: BackupRequest,
    bg: BackgroundTasks,
    current_user: dict = Depends(require_permission(Permission.BACKUP)),
):
    service = BackupService()

    def do_backup():
        service.create_backup(req.backup_type)

    bg.add_task(do_backup)
    return {
        "status": "started",
        "type": req.backup_type,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/list")
def list_backups(current_user: dict = Depends(require_permission(Permission.BACKUP))):
    service = BackupService()
    return {"backups": service.list_backups()}


@router.post("/restore")
def restore_backup(
    req: RestoreRequest,
    current_user: dict = Depends(require_permission(Permission.BACKUP)),
):
    service = BackupService()
    return service.restore_backup(req.filename, req.target_db, req.verify_only)


@router.post("/verify")
def verify_backups(current_user: dict = Depends(require_permission(Permission.BACKUP))):
    service = BackupService()
    return {"results": service.verify_all_backups()}


@router.post("/cleanup")
def cleanup_backups(
    current_user: dict = Depends(require_permission(Permission.BACKUP)),
):
    service = BackupService()
    return service.cleanup_old_backups()
