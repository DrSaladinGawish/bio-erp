"""
main_patch.py — Paste this into your main BIO-ERP app/main.py
Mounts Part 4 Launcher at /api/v1/launcher/
"""

# ── Add near top with other imports (after existing FastAPI imports) ──
import sys
from pathlib import Path

# Part 4 Launcher — resolve path to incentivehouse_organ/
_LAUNCHER_DIR = Path(__file__).parent / "app" / "organs" / "incentivehouse_organ"
if str(_LAUNCHER_DIR.resolve()) not in sys.path:
    sys.path.insert(0, str(_LAUNCHER_DIR.resolve()))

try:
    from launcher_dashboard_v4_0 import create_v4_app
    V4_AVAILABLE = True
except ImportError:
    V4_AVAILABLE = False


# ── Add after all other app.mount() calls, before if __name__ == "__main__" ──
# Mount Part 4 Launcher (Data Flow, AI Insights, Health Monitor)

if V4_AVAILABLE:
    v4_app = create_v4_app()
    app.mount("/api/v1/launcher", v4_app)
    print("[OK] Part 4 Launcher mounted at /api/v1/launcher/")
    print("      Dashboard: http://localhost:8000/api/v1/launcher/")
else:
    print("[WARN] Part 4 Launcher not found — expected at:")
    print(f"       {_LAUNCHER_DIR / 'launcher_dashboard_v4_0.py'}")
    print("       Run standalone: python launcher_dashboard_v4_0.py (port 9003)")
