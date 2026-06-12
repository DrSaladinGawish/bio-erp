"""
presentation_path_traversal_fix.py — Hardened Download Endpoint
Fix: Sanitize filename to prevent directory traversal (../../../etc/passwd)
"""

import os
import re
from pathlib import Path
from fastapi import HTTPException, status

# Allowed characters: alphanumeric, dash, underscore, dot
_SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
_MAX_FILENAME_LEN = 255
_UPLOADS_DIR = Path(os.getenv("PRESENTATIONS_DIR", "./uploads/presentations")).resolve()


def sanitize_filename(raw_name: str) -> str:
    """
    Sanitize user-supplied filename for safe filesystem access.
    Raises HTTPException 400 if filename is invalid or contains path traversal.
    """
    # Reject empty or overly long
    if not raw_name or len(raw_name) > _MAX_FILENAME_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: empty or too long",
        )

    # Reject path separators and traversal patterns
    if "/" in raw_name or "\\" in raw_name or ".." in raw_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path traversal detected",
        )

    # Reject hidden files and restrict to safe characters
    if raw_name.startswith(".") or not _SAFE_FILENAME_RE.match(raw_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: illegal characters",
        )

    return raw_name


def safe_file_path(filename: str) -> Path:
    """
    Resolve sanitized filename within uploads directory.
    Ensures final path is INSIDE _UPLOADS_DIR (prevents symlink escape).
    """
    safe_name = sanitize_filename(filename)
    target = (_UPLOADS_DIR / safe_name).resolve()

    # Final guard: ensure resolved path is still under uploads dir
    if not str(target).startswith(str(_UPLOADS_DIR)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path escape detected",
        )

    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    return target


# ── USAGE IN presentation_engine.py ──
# Replace:
#     @router.get("/download/{filename}")
#     def download(filename: str):
#         path = os.path.join(UPLOADS_DIR, filename)
#         return FileResponse(path)
#
# With:
#     @router.get("/download/{filename}")
#     def download(filename: str):
#         path = safe_file_path(filename)
#         return FileResponse(path)
