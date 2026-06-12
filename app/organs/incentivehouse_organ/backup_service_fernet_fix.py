"""
backup_service_fernet_fix.py — Hardened Backup Encryption
Fix: Fernet key loaded from env or file, NOT regenerated per run.
"""

import os
from cryptography.fernet import Fernet

# ── FERNET KEY MANAGEMENT ──
# Priority: 1) FERNET_KEY env var, 2) .fernet_key file, 3) Generate once and save


def get_fernet() -> Fernet:
    """Get or create persistent Fernet key. Key survives restarts."""

    # 1. Try environment variable
    env_key = os.getenv("FERNET_KEY")
    if env_key:
        try:
            f = Fernet(env_key.encode())
            return f
        except Exception:
            pass  # Invalid key format, fall through

    # 2. Try local key file
    key_file = os.path.join(os.path.dirname(__file__), ".fernet_key")
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            file_key = f.read().strip()
        try:
            fernet = Fernet(file_key)
            return fernet
        except Exception:
            pass  # Invalid key, fall through

    # 3. Generate new key and persist it
    new_key = Fernet.generate_key()
    with open(key_file, "wb") as f:
        f.write(new_key)
    os.chmod(key_file, 0o600)  # Restrict permissions

    # Also print instruction for env-based deployment
    print(f"[BACKUP] New Fernet key generated and saved to {key_file}")
    print(f"[BACKUP] For production, set env var: FERNET_KEY={new_key.decode()}")

    return Fernet(new_key)


# ── USAGE IN backup_service.py ──
# Replace:
#     self.fernet = Fernet(Fernet.generate_key())
# With:
#     self.fernet = get_fernet()
