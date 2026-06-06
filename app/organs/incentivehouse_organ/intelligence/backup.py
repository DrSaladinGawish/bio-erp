"""
intelligence/backup.py
Pre-change backup manager for IHE-ERP.
Adapted from Bio-ERP.  On SQLite (test) it does .backup; on SQL Server it issues
BACKUP DATABASE via the connection.  Failures are logged, never raised.
"""
from __future__ import annotations
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.organs.incentivehouse_organ.intelligence.audit import audit_event

logger = logging.getLogger("incentivehouse_organ.intelligence.backup")

BACKUP_DIR = Path(os.getenv("IHE_BACKUP_DIR", "./ihe_backups"))


def backup_before_change(
    db: Session,
    reason: str,
    user_id: str = "system",
) -> dict:
    """
    Take a backup of the live database before any structural change.

    On SQLite, copies the .db file.  On SQL Server, runs BACKUP DATABASE.
    Records an audit entry with action='BACKUP' on success.

    Returns a dict {status, path, timestamp, reason, error?}.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out: dict = {
        "status": "unknown",
        "path": None,
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
    }
    try:
        # Try SQL Server BACKUP DATABASE first
        try:
            db.execute(text(f"BACKUP DATABASE IHE_ERP TO DISK = N'{BACKUP_DIR}/IHE_ERP_{ts}.bak'"))
            db.commit()
            out["status"] = "ok"
            out["path"] = f"{BACKUP_DIR}/IHE_ERP_{ts}.bak"
        except Exception:
            # Fall back to SQLite file copy
            db_url = str(db.bind.url) if db.bind else ""
            if "sqlite" in db_url:
                # Extract the DB file path from the URL
                path_part = db_url.split("///")[-1].split("?")[0]
                if path_part and Path(path_part).exists():
                    dest = BACKUP_DIR / f"{Path(path_part).stem}_{ts}.db"
                    shutil.copy2(path_part, dest)
                    out["status"] = "ok"
                    out["path"] = str(dest)
                else:
                    out["status"] = "skipped"
                    out["path"] = None
            else:
                out["status"] = "skipped"
                out["path"] = None
    except Exception as exc:
        logger.warning("backup_before_change failed: %s", exc)
        out["status"] = "error"
        out["error"] = str(exc)

    # Always record the attempt in audit_trail
    try:
        audit_event(db, "system", None, "BACKUP", None, out, user_id=user_id)
    except Exception:
        pass

    return out


def list_backups() -> list:
    """List all backups in the BACKUP_DIR."""
    if not BACKUP_DIR.exists():
        return []
    out = []
    for f in sorted(BACKUP_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix in (".bak", ".db", ".sql"):
            out.append({
                "name": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return out[:50]
