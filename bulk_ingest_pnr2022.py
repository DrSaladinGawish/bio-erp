"""
bulk_ingest_pnr2022.py — Copy PNR files to archive, generate batch JSONL for DB import
"""

import csv, json, hashlib, shutil, sys
from datetime import datetime
from pathlib import Path

PNR_SOURCE = Path(
    r"D:\flash memory\USB Drive\INCENTIVE HOUSE OF EGYPT\Book Keeping\Master Data\Work Order Maset Data\PNR-2022"
)
ARCHIVE_ROOT = Path(r"D:\Data_Sources\docs\Events\Work_Orders")
REPORT_DIR = Path(r"D:\Data_Sources\docs\PNR-2022-analysis")
BATCH_LOG = ARCHIVE_ROOT / "ingest_batch.jsonl"

DRY_RUN = "--dry-run" in sys.argv


def sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_normalization_map():
    csv_path = REPORT_DIR / "pnr_normalization_map.csv"
    if not csv_path.exists():
        print(f"ERROR: Run analyze_pnr2022.py first — {csv_path} not found")
        sys.exit(1)
    with open(csv_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    print("=== PNR-2022 Bulk Ingest ===")
    if DRY_RUN:
        print("[DRY RUN — no files will be copied]")

    pnr_map = load_normalization_map()
    print(f"Loaded {len(pnr_map)} entries from normalization map")

    folders_processed = 0
    files_copied = 0
    files_linked = 0
    files_orphaned = 0
    errors = 0
    total_bytes = 0
    batch = []

    # Group by normalized PNR for deduplication
    seen_hashes = set()

    for entry in pnr_map:
        folder_path = entry.get("folder_path", "")
        if not folder_path or not Path(folder_path).exists():
            continue
        folder = Path(folder_path)
        year = entry.get("year", "2026")
        normalized = entry.get("normalized", folder.name)
        client_code = entry.get("client_code", "")
        client_name = entry.get("client_name", "Unknown")

        # Archive path: D:\Data_Sources\docs\Events\Work_Orders\YYYY\normalized_pnr\
        archive_dir = (
            ARCHIVE_ROOT / year / f"{normalized}_{client_name.replace(' ', '_')}"
        )
        archive_dir.mkdir(parents=True, exist_ok=True)

        files = sorted(f for f in folder.iterdir() if f.is_file())
        if not files:
            folders_processed += 1
            continue

        for file_path in files:
            try:
                fhash = sha256(file_path)
                if fhash in seen_hashes:
                    continue
                seen_hashes.add(fhash)

                fsize = file_path.stat().st_size
                ext = file_path.suffix.lstrip(".").lower()
                archive_path = archive_dir / file_path.name

                if DRY_RUN:
                    print(f"  Would copy: {file_path.name} → {archive_path}")
                else:
                    shutil.copy2(file_path, archive_path)

                total_bytes += fsize

                # Determine link status
                auto_link = bool(client_code and normalized)
                txn_id = normalized if auto_link else "orphaned"
                status = "linked" if auto_link else "orphaned"
                if auto_link:
                    files_linked += 1
                else:
                    files_orphaned += 1

                record = {
                    "module_name": "Events",
                    "function_name": "Work_Orders",
                    "transaction_table": "work_orders",
                    "transaction_id": txn_id,
                    "original_usb_path": str(file_path),
                    "archive_path": str(archive_path),
                    "file_hash_sha256": fhash,
                    "file_size_bytes": fsize,
                    "file_name": file_path.name,
                    "file_ext": ext,
                    "status": status,
                    "uploaded_by": "pnr2022_bulk_ingest",
                }
                batch.append(record)
                files_copied += 1

            except Exception as e:
                print(f"  ERROR: {file_path}: {e}")
                errors += 1

        folders_processed += 1
        if folders_processed % 10 == 0:
            print(f"  ... {folders_processed} folders done ({files_copied} files)")

    # Write batch JSONL
    if not DRY_RUN:
        BATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(BATCH_LOG, "w", encoding="utf-8") as f:
            for rec in batch:
                f.write(json.dumps(rec, default=str) + "\n")
        print(f"✅ Batch log: {BATCH_LOG} ({len(batch)} records)")

    total_mb = total_bytes / (1024 * 1024)
    print(f"\n📁 Folders processed: {folders_processed}")
    print(f"📄 Files copied: {files_copied}")
    print(f"🔗 Files linked: {files_linked}")
    print(f"⚠️  Files orphaned: {files_orphaned}")
    print(f"❌ Errors: {errors}")
    print(f"💾 Total size: {total_mb:.1f} MB")
    print(f"📂 Archive: {ARCHIVE_ROOT}")
    print()
    if not DRY_RUN:
        print(f"Next: python import_pnr2022_db.py")
    else:
        print("Run without --dry-run to execute")


if __name__ == "__main__":
    main()
