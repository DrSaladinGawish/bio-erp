#!/usr/bin/env python3
"""
IncentiveHouse ERP — Pre-Flight Health Check
============================================
Validates environment, dependencies, and connectivity before deploy.
Run: python scripts/health_check.py
Exit code 0 = safe to deploy, 1 = fix issues first.
"""
import os
import sys
import socket
import subprocess
from pathlib import Path

# Required environment variables
REQUIRED_ENVS = [
    "DATABASE_URL",
    "SECRET_KEY",
]

# Optional service ports (warn but don't fail)
OPTIONAL_PORTS = {
    5432: "PostgreSQL",
    6379: "Redis",
    8025: "Mailhog",
}

# Critical Python packages
REQUIRED_PACKAGES = [
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "pydantic",
    "openpyxl",
]


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def check_env() -> bool:
    section("Environment Variables")
    missing = [e for e in REQUIRED_ENVS if not os.getenv(e)]
    if missing:
        print(f"  [FAIL] Missing: {', '.join(missing)}")
        print(f"         Set them in .env or export before running")
        return False
    for e in REQUIRED_ENVS:
        val = os.getenv(e, "")
        masked = val[:8] + "***" if "KEY" in e or "PASS" in e or "URL" in e else val
        print(f"  [OK]   {e} = {masked}")
    return True


def check_python_version() -> bool:
    section("Python Version")
    v = sys.version_info
    print(f"  Python {v.major}.{v.minor}.{v.micro}")
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print("  [FAIL] Python 3.10+ required")
        return False
    print("  [OK]   Version meets requirement (3.10+)")
    return True


def check_packages() -> bool:
    section("Python Packages")
    ok = True
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
            print(f"  [OK]   {pkg}")
        except ImportError:
            print(f"  [FAIL] {pkg} not installed")
            ok = False
    return ok


def check_ports() -> bool:
    section("Optional Services")
    for port, name in OPTIONAL_PORTS.items():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(("localhost", port)) == 0:
                print(f"  [OK]   Port {port} ({name}) open")
            else:
                print(f"  [WARN] Port {port} ({name}) closed (optional)")
    return True  # All optional, never fail


def check_database() -> bool:
    section("Database Connectivity")
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("  [SKIP] DATABASE_URL not set")
        return True
    try:
        # Try psycopg2/psycopg
        try:
            import psycopg2
            conn = psycopg2.connect(db_url, connect_timeout=3)
            cur = conn.cursor()
            cur.execute("SELECT version();")
            ver = cur.fetchone()[0]
            conn.close()
            print(f"  [OK]   Connected: {ver[:60]}")
            return True
        except ImportError:
            pass
        try:
            import psycopg
            conn = psycopg.connect(db_url, connect_timeout=3)
            ver = conn.execute("SELECT version();").fetchone()[0]
            conn.close()
            print(f"  [OK]   Connected: {ver[:60]}")
            return True
        except ImportError:
            pass
        print("  [WARN] No postgres driver installed (psycopg2/psycopg)")
        return True
    except Exception as exc:
        print(f"  [FAIL] Cannot connect: {exc}")
        return False


def check_migrations() -> bool:
    section("Database Migrations")
    mig_dirs = [
        Path("alembic/versions"),
        Path("migrations"),
    ]
    for d in mig_dirs:
        if d.exists():
            files = sorted(d.glob("*.py"))
            files = [f for f in files if not f.name.startswith("__")]
            print(f"  [OK]   {d}: {len(files)} migration(s)")
            for f in files[-3:]:
                print(f"         - {f.name}")
            return True
    print("  [WARN] No alembic/ or migrations/ directory found")
    return True


def check_disk_space() -> bool:
    section("Disk Space")
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        free_gb = free / (1024 ** 3)
        print(f"  Free: {free_gb:.1f} GB")
        if free_gb < 1.0:
            print("  [FAIL] Less than 1 GB free")
            return False
        print("  [OK]   Sufficient disk space")
        return True
    except Exception as exc:
        print(f"  [WARN] Cannot check: {exc}")
        return True


def check_templates() -> bool:
    section("Templates")
    tpl_dir = Path("templates")
    if not tpl_dir.exists():
        print("  [WARN] templates/ not found")
        return True
    htmls = list(tpl_dir.glob("*.html"))
    print(f"  [OK]   {len(htmls)} HTML template(s) found:")
    for t in sorted(htmls):
        size = t.stat().st_size
        print(f"         - {t.name}  ({size:,} bytes)")
    return True


def main() -> int:
    print("\n" + "=" * 60)
    print("  IncentiveHouse ERP — Pre-Flight Health Check")
    print("  v2.0.0 • Bio-ERP")
    print("=" * 60)

    results = [
        check_python_version(),
        check_env(),
        check_packages(),
        check_ports(),
        check_database(),
        check_migrations(),
        check_disk_space(),
        check_templates(),
    ]

    section("Summary")
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"  Checks passed: {passed}/{total}")

    if all(results):
        print("\n  [OK] All checks passed. Safe to deploy.\n")
        return 0
    else:
        print("\n  [FAIL] Fix the issues above before deploying.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
