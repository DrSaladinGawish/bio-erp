"""
analyze_pnr2022.py — Scan PNR-2022, normalize PNR codes, map clients, classify docs, report anomalies
"""

import csv, json, re, sys, unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PNR_SOURCE = Path(
    r"D:\flash memory\USB Drive\INCENTIVE HOUSE OF EGYPT\Book Keeping\Master Data\Work Order Maset Data\PNR-2022"
)
ARCHIVE_ROOT = Path(r"D:\Data_Sources\docs\Events\Work_Orders")
REPORT_DIR = Path(r"D:\Data_Sources\docs\PNR-2022-analysis")

CLIENT_CODES = {
    "C0001": "Abbott",
    "C0003": "Microsoft",
    "C0006": "CISCO",
    "C002": "Unknown_Bank",
    "C001": "Unknown_Large",
    "C0029": "CBE",
    "C0031": "E-Finance",
    "C0033": "Orion 360",
    "C0038": "USAID",
    "C0180": "TEAMSTOCK",
    "C0181": "Unknown_181",
}


def normalize_pnr(folder_name, year):
    folder = folder_name.strip()
    original = folder
    anomalies = []

    # Check for Arabic characters
    if any(unicodedata.category(c) == "Lo" for c in folder):
        folder = re.sub(
            r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\s]+", "", folder
        ).strip()
        anomalies.append(("arabic_name", original))

    # Remove common suffixes
    folder = re.sub(r"\s*-\s*Invoiced.*", "", folder, flags=re.IGNORECASE)
    folder = re.sub(r"\s*INV\s*\d+[-–]\d+", "", folder, flags=re.IGNORECASE)
    folder = re.sub(r"\s+invoiced\s+\d+[-–]\d+", "", folder, flags=re.IGNORECASE)
    folder = re.sub(r"\s{2,}", " ", folder).strip()

    # Try mm.yy.CCCC.SSS pattern (e.g., 09.22.C002.001)
    m = re.match(r"^(\d{1,2})\.(\d{2})\.(C\d{3,4})\.(\d{3})$", folder)
    if m:
        month, yy, client, seq = m.groups()
        full_year = f"20{yy}"
        return {
            "original": original,
            "normalized": folder,
            "year": full_year,
            "month": month,
            "client_code": client,
            "client_name": CLIENT_CODES.get(client, "Unknown"),
            "seq": seq,
            "anomalies": anomalies,
        }

    # Try mm.yy.CCCC.SSS-Description (e.g., 01.24.C0003.76 MS)
    m = re.match(r"^(\d{1,2})\.(\d{2})\.(C\d{3,4})\.(\d{3})\s+(.+)$", folder)
    if m:
        month, yy, client, seq, desc = m.groups()
        full_year = f"20{yy}"
        return {
            "original": original,
            "normalized": f"{month}.{yy}.{client}.{seq}",
            "year": full_year,
            "month": month,
            "client_code": client,
            "client_name": CLIENT_CODES.get(client, "Unknown"),
            "seq": seq,
            "description": desc.strip(),
            "anomalies": anomalies,
        }

    # Try seq-yyyy-C-CCCC-SS ClientName (e.g., 10-2023-C-0006-72 Cisco)
    m = re.match(r"^(\d{1,2})-(\d{4})-C-(\d{4})-(\d+)\s+(.+)$", folder)
    if m:
        month, full_year, client_num, seq, desc = m.groups()
        client_code = f"C{client_num}"
        return {
            "original": original,
            "normalized": f"{month}.{full_year[-2:]}.{client_code}.{seq.zfill(3)}",
            "year": full_year,
            "month": month,
            "client_code": client_code,
            "client_name": CLIENT_CODES.get(client_code, "Unknown"),
            "seq": seq,
            "description": desc.strip(),
            "anomalies": anomalies,
        }

    # Try mm.yy.CCCC.SS ClientName (e.g., 01.24.C0003.76 MS)
    m = re.match(r"^(\d{1,2})\.(\d{2})\.(C\d{3,4})\.(\d{2})\s+(.+)$", folder)
    if m:
        month, yy, client, seq, desc = m.groups()
        full_year = f"20{yy}"
        return {
            "original": original,
            "normalized": f"{month}.{yy}.{client}.{seq.zfill(3)}",
            "year": full_year,
            "month": month,
            "client_code": client,
            "client_name": CLIENT_CODES.get(client, "Unknown"),
            "seq": seq.zfill(3),
            "description": desc.strip(),
            "anomalies": anomalies,
        }

    # Try mm.yy.CCCC.SS (short seq)
    m = re.match(r"^(\d{1,2})\.(\d{2})\.(C\d{3,4})\.(\d{2})$", folder)
    if m:
        month, yy, client, seq = m.groups()
        full_year = f"20{yy}"
        return {
            "original": original,
            "normalized": f"{month}.{yy}.{client}.{seq.zfill(3)}",
            "year": full_year,
            "month": month,
            "client_code": client,
            "client_name": CLIENT_CODES.get(client, "Unknown"),
            "seq": seq.zfill(3),
            "anomalies": anomalies,
        }

    anomalies.append(("unrecognized_format", original))
    return {
        "original": original,
        "normalized": folder,
        "year": year,
        "month": "",
        "client_code": "",
        "client_name": "Unknown",
        "seq": "",
        "anomalies": anomalies,
    }


def classify_files(files):
    pdfs = jpgs = xlsxs = docs = others = 0
    for f in files:
        ext = f.suffix.lower()
        if ext == ".pdf":
            pdfs += 1
        elif ext in (".jpg", ".jpeg", ".png", ".tiff", ".tif"):
            jpgs += 1
        elif ext in (".xlsx", ".xls", ".csv"):
            xlsxs += 1
        elif ext in (".doc", ".docx"):
            docs += 1
        else:
            others += 1
    return {"pdf": pdfs, "jpg": jpgs, "xlsx": xlsxs, "doc": docs, "other": others}


def main():
    print("=== PNR-2022 Analysis ===")
    if not PNR_SOURCE.exists():
        print(f"ERROR: Source not found: {PNR_SOURCE}")
        sys.exit(1)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    all_folders = []
    all_files = []
    summary = defaultdict(
        lambda: {"folders": 0, "files": 0, "by_client": defaultdict(int)}
    )
    anomaly_list = []
    client_stats = defaultdict(lambda: {"folders": 0, "files": 0})
    pnr_map = []

    year_dirs = sorted(
        [d for d in PNR_SOURCE.iterdir() if d.is_dir() and d.name != "SYSTEM EXCEL"]
    )

    for year_dir in year_dirs:
        year_label = year_dir.name
        print(f"\n📁 Scanning {year_label}/ ...")

        # Determine actual year from folder name
        actual_year = year_label[:4] if year_label[:4].isdigit() else "2026"

        work_folders = sorted([d for d in year_dir.iterdir() if d.is_dir()])
        loose_files = sorted([f for f in year_dir.iterdir() if f.is_file()])

        summary[actual_year]["folders"] += len(work_folders)
        summary[actual_year]["files"] += len(loose_files)

        for wf in work_folders:
            files = sorted(wf.iterdir())
            all_files.extend(files)

            pnr_info = normalize_pnr(wf.name, actual_year)
            pnr_info["year_label"] = year_label
            pnr_info["folder_path"] = str(wf)
            pnr_info["file_count"] = len(files)
            pnr_info["file_types"] = classify_files(files)
            pnr_info["total_size_bytes"] = sum(
                f.stat().st_size for f in files if f.is_file()
            )

            if pnr_info["anomalies"]:
                for a in pnr_info["anomalies"]:
                    anomaly_list.append(
                        {"folder": str(wf), "type": a[0], "original": a[1]}
                    )

            client = pnr_info["client_name"]
            client_stats[client]["folders"] += 1
            client_stats[client]["files"] += len(files)
            summary[actual_year]["by_client"][client] += 1

            pnr_map.append(pnr_info)
            all_folders.append(wf)

        if loose_files:
            for lf in loose_files:
                pnr_map.append(
                    {
                        "original": lf.name,
                        "normalized": lf.name,
                        "year": actual_year,
                        "month": "",
                        "client_code": "",
                        "client_name": "Loose",
                        "seq": "",
                        "year_label": year_label,
                        "folder_path": str(year_dir),
                        "file_count": 0,
                        "file_types": {},
                        "total_size_bytes": lf.stat().st_size,
                        "description": "loose file in year root",
                        "anomalies": [],
                    }
                )

    total_folders = len(all_folders)
    total_files = len(all_files)
    total_size_mb = sum(f.stat().st_size for f in all_files) / (1024 * 1024)

    print(f"\n📊 Total folders: {total_folders}")
    print(f"📄 Total files: {total_files}")
    print(f"💾 Total size: {total_size_mb:.1f} MB")
    print(f"⚠️  Anomalies found: {len(anomaly_list)}")
    print()

    print("📅 By Year:")
    for yr in sorted(summary.keys()):
        s = summary[yr]
        print(f"  {yr}: {s['folders']} folders, ~{s['files']} files")
    print()

    print("🏢 By Client:")
    for client, stats in sorted(client_stats.items(), key=lambda x: -x[1]["files"]):
        print(f"  {client}: {stats['folders']} folders, {stats['files']} files")

    if anomaly_list:
        print(f"\n⚠️  Anomaly Breakdown ({len(anomaly_list)} total):")
        by_type = defaultdict(list)
        for a in anomaly_list:
            by_type[a["type"]].append(a)
        for atype, items in sorted(by_type.items()):
            print(f"  {atype}: {len(items)}")
            for item in items[:3]:
                print(f"    - {item['folder']}")

    # Save reports
    csv_path = REPORT_DIR / "pnr_normalization_map.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "original",
                "normalized",
                "year",
                "month",
                "client_code",
                "client_name",
                "seq",
                "description",
                "file_count",
                "total_size_bytes",
                "folder_path",
                "anomalies",
            ],
        )
        w.writeheader()
        for p in pnr_map:
            row = {k: p.get(k, "") for k in w.fieldnames}
            row["anomalies"] = "; ".join(
                f"{a[0]}:{a[1]}" for a in p.get("anomalies", [])
            )
            w.writerow(row)
    print(f"\n✅ Normalization map: {csv_path}")

    with open(REPORT_DIR / "anomaly_report.json", "w", encoding="utf-8") as f:
        json.dump(anomaly_list, f, indent=2, ensure_ascii=False)
    print(f"✅ Anomaly report: {REPORT_DIR / 'anomaly_report.json'}")

    with open(REPORT_DIR / "client_mapping.json", "w", encoding="utf-8") as f:
        json.dump(dict(sorted(client_stats.items())), f, indent=2, default=str)
    print(f"✅ Client mapping: {REPORT_DIR / 'client_mapping.json'}")

    with open(REPORT_DIR / "summary_report.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_folders": total_folders,
                "total_files": total_files,
                "total_size_mb": round(total_size_mb, 1),
                "anomalies": len(anomaly_list),
                "by_year": {k: dict(v) for k, v in summary.items()},
                "by_client": dict(
                    sorted(client_stats.items(), key=lambda x: -x[1]["files"])
                ),
            },
            f,
            indent=2,
            default=str,
        )
    print(f"✅ Summary report: {REPORT_DIR / 'summary_report.json'}")

    print(f"\n{'=' * 50}")
    print(f"📁 Next: Review anomalies at {REPORT_DIR / 'anomaly_report.json'}")
    print(f"📁 Then run: python bulk_ingest_pnr2022.py")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
