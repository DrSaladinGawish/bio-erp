import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
ARCHIVE_ROOT = BASE_DIR / "archive"


def ensure_archive_dir() -> Path:
    now = datetime.utcnow()
    archive_dir = ARCHIVE_ROOT / str(now.year) / f"{now.month:02d}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


def archive_file(source_path: str, filename: str) -> str:
    src = Path(source_path)
    if not src.exists():
        logger.warning("Source file not found for archiving: %s", source_path)
        return ""
    archive_dir = ensure_archive_dir()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest_path = archive_dir / f"{timestamp}_{filename}"
    try:
        shutil.copy2(str(src), str(dest_path))
        logger.info("Archived %s -> %s", src.name, dest_path)
        return str(dest_path)
    except Exception as e:
        logger.error("Archive failed for %s: %s", source_path, e)
        return ""
