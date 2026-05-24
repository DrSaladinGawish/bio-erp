import os
import subprocess
from datetime import datetime, timezone
from celery import shared_task

_BACKUP_DIR = os.getenv("BACKUP_DIR", "/backups")
_RETENTION_DAYS = 7


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def create_db_backup(self):
    os.makedirs(_BACKUP_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"bio_erp_{ts}.dump"
    filepath = os.path.join(_BACKUP_DIR, filename)

    host = os.getenv("PGHOST", "postgres")
    user = os.getenv("PGUSER", "bioerp")
    password = os.getenv("PGPASSWORD", "bioerp")
    dbname = os.getenv("PGDATABASE", "bio_erp")

    env = os.environ.copy()
    env["PGPASSWORD"] = password

    try:
        result = subprocess.run(
            ["pg_dump", "-Fc", "-h", host, "-U", user, "-d", dbname, "-f", filepath],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {result.stderr}")

        size = os.path.getsize(filepath)
        _cleanup_old_backups()

        return {
            "status": "success",
            "file": filename,
            "size_bytes": size,
            "size_mb": round(size / (1024 * 1024), 2),
        }
    except Exception as exc:
        raise self.retry(exc=exc)


def _cleanup_old_backups():
    if not os.path.isdir(_BACKUP_DIR):
        return
    now = datetime.utcnow().timestamp()
    for fname in os.listdir(_BACKUP_DIR):
        fpath = os.path.join(_BACKUP_DIR, fname)
        if not fname.endswith(".dump") or not os.path.isfile(fpath):
            continue
        age_hours = (now - os.path.getmtime(fpath)) / 3600
        if age_hours > _RETENTION_DAYS * 24:
            os.remove(fpath)
