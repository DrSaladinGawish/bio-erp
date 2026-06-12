"""
ingest_2024_monthly.py — Scan 2024 monthly archives, copy files, generate batch JSONL

Folder hierarchy at USB root:
  Book Keeping\Master Data\Historical Master Data\YEAR 2024 Working Files\2024\Archive\
    Financial Transaction Supporting Documents\2024\{=Mon-YY}\  → Bank/Statements
    Sales Invoices\2024\{Mon-YY}\                              → Sales/Invoices
    Purshase Invoices\2024\{Mon-YY}\                           → Purchase/Vendor_Invoices
    VAT Report\2024\{Mon-YY}\                                  → E_Invoice/Submissions
    MONTHLY CLOSING\{files}                                    → Bank/Statements (monthly closing docs)
"""

import hashlib, json, shutil, sys
from pathlib import Path

USB_ARCHIVE = Path(
    r"D:\flash memory\USB Drive\INCENTIVE HOUSE OF EGYPT\Book Keeping\Master Data\Historical Master Data\YEAR 2024 Working Files\2024\Archive"
)
ARCHIVE_ROOT = Path(r"D:\Data_Sources\docs\2024-Monthly")
BATCH_LOG = ARCHIVE_ROOT / "ingest_batch.jsonl"

MODULE_MAP = {
    "Financial Transaction Supporting Documents": ("Bank", "Statements"),
    "Sales Invoices": ("Sales", "Invoices"),
    "Purshase Invoices": ("Purchase", "Vendor_Invoices"),
    "VAT Report": ("E_Invoice", "Submissions"),
    "MONTHLY CLOSING": ("Bank", "Statements"),
}

DRY_RUN = "--dry-run" in sys.argv


def sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_category(cat_name, cat_path):
    module, function = MODULE_MAP[cat_name]
    records = []
    if not cat_path.exists():
        return records
    if cat_name == "MONTHLY CLOSING":
        for fpath in sorted(cat_path.iterdir()):
            if fpath.is_file() and not fpath.name.startswith("~"):
                records.append((fpath, module, function))
        return records
    for month_dir in sorted(cat_path.iterdir()):
        if not month_dir.is_dir():
            continue
        for fpath in sorted(month_dir.iterdir()):
            if fpath.is_file() and not fpath.name.startswith("~"):
                records.append((fpath, module, function))
    return records


def main():
    print("=== 2024 Monthly Archive Ingest ===")
    if DRY_RUN:
        print("[DRY RUN — no files will be copied]")

    batch = []
    files_copied = 0
    errors = 0
    total_bytes = 0
    seen_hashes = set()
    cat_counts = {}

    for cat_name in sorted(MODULE_MAP):
        module, function = MODULE_MAP[cat_name]
        if cat_name == "MONTHLY CLOSING":
            cat_path = USB_ARCHIVE / cat_name
        else:
            cat_path = USB_ARCHIVE / cat_name / "2024"
        items = scan_category(cat_name, cat_path)
        cat_counts[cat_name] = len(items)
        print(f"  {cat_name}: {len(items)} files")

        for fpath, module, function in items:
            try:
                fhash = sha256(fpath)
                if fhash in seen_hashes:
                    continue
                seen_hashes.add(fhash)

                fsize = fpath.stat().st_size
                ext = fpath.suffix.lstrip(".").lower()
                archive_dir = ARCHIVE_ROOT / cat_name
                archive_dir.mkdir(parents=True, exist_ok=True)
                archive_path = archive_dir / fpath.name

                if not DRY_RUN:
                    shutil.copy2(fpath, archive_path)

                total_bytes += fsize

                record = {
                    "module_name": module,
                    "function_name": function,
                    "transaction_table": "",
                    "transaction_id": "monthly_2024",
                    "original_usb_path": str(fpath),
                    "archive_path": str(archive_path),
                    "file_hash_sha256": fhash,
                    "file_size_bytes": fsize,
                    "file_name": fpath.name,
                    "file_ext": ext,
                    "status": "linked",
                    "uploaded_by": "ingest_2024_monthly",
                }
                batch.append(record)
                files_copied += 1

            except Exception as e:
                print(f"  ERROR: {fpath}: {e}")
                errors += 1

    if not DRY_RUN:
        BATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(BATCH_LOG, "w", encoding="utf-8") as f:
            for rec in batch:
                f.write(json.dumps(rec, default=str) + "\n")
        print(f"  Batch log: {BATCH_LOG} ({len(batch)} records)")

    total_mb = total_bytes / (1024 * 1024)
    print(f"\nFiles copied: {files_copied}")
    print(f"Errors: {errors}")
    print(f"Total size: {total_mb:.1f} MB")
    print(f"Archive: {ARCHIVE_ROOT}")
    print()
    if not DRY_RUN:
        print("Next: python import_2024_monthly_db.py")
    else:
        print("Run without --dry-run to execute")


if __name__ == "__main__":
    main()
