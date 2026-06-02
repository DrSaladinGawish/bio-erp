import uuid
from pathlib import Path

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"


def ensure_upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def save_upload(file_bytes: bytes, original_filename: str) -> str:
    upload_dir = ensure_upload_dir()
    stem = Path(original_filename).stem
    ext = Path(original_filename).suffix
    unique_name = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
    dest = upload_dir / unique_name
    dest.write_bytes(file_bytes)
    return str(dest)
