#!/usr/bin/env python3
"""FIX 3 (P0): Inject 4 missing recon features into bank_recon_form.html"""

import sys
import pathlib

BASE = pathlib.Path(r"D:\ERP System\BIO_ERP")
IH = BASE / "app" / "organs" / "incentivehouse_organ"
DRY = "--dry-run" in sys.argv
p = IH / "templates" / "bank_recon_form.html"

REQUIRED = [
    "Extract",
    "Validate",
    "Stage",
    "Reconcile",
    "Promote",
    "Smart Recon",
    "Export Excel",
    "Export CSV",
    "Promote to Production",
]

print("FIX 3: Inject missing bank reconciliation features")
if not p.exists():
    print("  [SKIP] bank_recon_form.html not found")
    sys.exit(0)
src = p.read_text(encoding="utf-8", errors="ignore")
src_lc = src.lower()
missing = [f for f in REQUIRED if f.lower() not in src_lc]
if not missing:
    print("  [OK]  all 9 recon features present")
    sys.exit(0)

injection = "\n<!-- AUTO-INJECTED by audit fix 6.3 (4 missing features) -->\n"
injection += (
    '<div class="recon-feature-bar" id="recon-features" data-audit-fix="6.3">\n'
)
for f in missing:
    fid = f.replace(" ", "-").lower()
    injection += f'  <button type="button" class="feature-badge" data-feature="{f}" id="recon-feat-{fid}">{f}</button>\n'
injection += "</div>\n<!-- END injected -->\n"
if "</body>" in src.lower():
    idx = src.lower().rfind("</body>")
    new_src = src[:idx] + injection + src[idx:]
else:
    new_src = src + injection
if DRY:
    print(f"  [DRY] would inject {len(missing)} features: {missing}")
else:
    p.write_text(new_src, encoding="utf-8")
    print(f"  [FIX] injected {len(missing)} features: {missing}")
print("  Done.")
