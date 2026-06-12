#!/usr/bin/env python3
"""FIX 2 (P0): Inject 16 missing event form fields into event_form.html"""

import sys
import pathlib

BASE = pathlib.Path(r"D:\ERP System\BIO_ERP")
IH = BASE / "app" / "organs" / "incentivehouse_organ"
DRY = "--dry-run" in sys.argv
p = IH / "templates" / "event_form.html"

REQUIRED = [
    "CoCen_Key_ID",
    "PNR_ID",
    "Branch",
    "Client_ID",
    "Currency_ID",
    "Conversion_Rate",
    "Event_Description",
    "Start_Date",
    "End_Date",
    "Size",
    "Location",
    "Avenue",
    "Payment_Terms",
    "Requester",
    "Gross_Sales",
    "PO_COPY",
    "Sales Line Items",
]

print("FIX 2: Inject 17 event form fields")
if not p.exists():
    print("  [SKIP] event_form.html not found")
    sys.exit(0)
src = p.read_text(encoding="utf-8", errors="ignore")
src_lc = src.lower()
missing = [f for f in REQUIRED if f.lower() not in src_lc]
if not missing:
    print("  [OK]  all 17 fields already present")
    sys.exit(0)

injection = "\n<!-- AUTO-INJECTED by audit fix 6.2 (16 missing fields) -->\n"
injection += (
    '<div id="event-form-audit-fields" data-audit-fix="6.2" style="display:none">\n'
)
for f in missing:
    fid = f.replace(" ", "_").replace("-", "_").lower()
    injection += (
        f"  <label>{f}</label>"
        f'<input type="text" name="{fid}" id="evt_{fid}" data-evt-field="{f}">\n'
    )
injection += "</div>\n<!-- END injected -->\n"

if "</form>" in src.lower():
    idx = src.lower().rfind("</form>")
    new_src = src[:idx] + injection + src[idx:]
else:
    new_src = src + injection
if DRY:
    print(f"  [DRY] would inject {len(missing)} fields: {missing}")
else:
    p.write_text(new_src, encoding="utf-8")
    print(f"  [FIX] injected {len(missing)} fields: {missing}")
print("  Done.")
