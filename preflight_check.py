#!/usr/bin/env python3
"""
ERP Builder Protocol — Pre-Flight Health Check
Run before docker-compose up to validate environment.
"""
import sys
import socket
import subprocess
import os
from pathlib import Path

REQUIRED_ENVS = ["DATABASE_URL", "SECRET_KEY", "ENVIRONMENT"]
OPTIONAL_PORTS = [5432, 6379, 8025]  # Postgres, Redis, Mailhog

def check_env():
    missing = [e for e in REQUIRED_ENVS if not os.getenv(e)]
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}")
        return False
    print("✅ Environment variables")
    return True

def check_ports():
    ok = True
    for port in OPTIONAL_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) == 0:
                print(f"✅ Port {port} open")
            else:
                print(f"⚠️  Port {port} closed (optional)")
    return ok

def check_migrations():
    mig_dir = Path("alembic/versions")
    if not mig_dir.exists():
        print("⚠️  No alembic migrations directory")
        return True
    files = list(mig_dir.glob("*.py"))
    print(f"✅ {len(files)} migration files found")
    return True

def main():
    print("🔍 IncentiveHouse ERP Pre-Flight Check\n")
    results = [
        check_env(),
        check_ports(),
        check_migrations(),
    ]
    if all(results):
        print("\n🚀 All checks passed. Safe to deploy.")
        sys.exit(0)
    else:
        print("\n⛔ Fix issues before deploying.")
        sys.exit(1)

if __name__ == "__main__":
    main()
