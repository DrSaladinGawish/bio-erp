#!/bin/bash
# =============================================================================
# IncentiveHouse ERP — PostgreSQL Backup
# =============================================================================
# Run via cron:  0 2 * * * /opt/incentivehouse/scripts/db_backup.sh >> /var/log/erp-backup.log 2>&1
# Restore:       pg_restore -d erp /backups/erp_backup_YYYYMMDD_HHMMSS.dump
# =============================================================================
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
DB_NAME="${DB_NAME:-erp}"
COMPRESS="${COMPRESS:-gzip}"

# Load .env if present
if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

# Fallback: parse DATABASE_URL
if [ -z "${DATABASE_URL:-}" ]; then
    echo "[ERROR] DATABASE_URL not set and no .env file found"
    exit 1
fi

# Try to extract components from URL (postgresql://user:pass@host:port/dbname)
if [[ "${DATABASE_URL}" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/([^?]+) ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASS="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    DB_NAME="${BASH_REMATCH[5]}"
elif [[ "${DATABASE_URL}" =~ postgresql://([^:]+):([^@]+)@([^/]+)/([^?]+) ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASS="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="5432"
    DB_NAME="${BASH_REMATCH[4]}"
else
    # Use PGPASSWORD + let pg_dump use the URL directly
    DB_HOST=""
fi

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/erp_backup_${TIMESTAMP}.dump"

# ── Pre-flight ───────────────────────────────────────────────────────────────
echo "============================================================"
echo "  IncentiveHouse ERP — DB Backup"
echo "  Timestamp:  ${TIMESTAMP}"
echo "  Database:   ${DB_NAME}"
echo "  Output:     ${BACKUP_FILE}"
echo "============================================================"

if ! command -v pg_dump &> /dev/null; then
    echo "[ERROR] pg_dump not found. Install postgresql-client."
    exit 1
fi

# ── Execute backup ───────────────────────────────────────────────────────────
export PGPASSWORD="${DB_PASS:-}"

if [ -n "${DB_HOST:-}" ]; then
    pg_dump \
        --host="$DB_HOST" \
        --port="${DB_PORT:-5432}" \
        --username="${DB_USER:-postgres}" \
        --dbname="$DB_NAME" \
        --format=custom \
        --compress=9 \
        --no-owner \
        --no-privileges \
        --verbose \
        --file="$BACKUP_FILE" 2>&1 | tee -a "$BACKUP_DIR/backup.log"
else
    # Use URL directly
    pg_dump "$DATABASE_URL" \
        --format=custom \
        --compress=9 \
        --no-owner \
        --no-privileges \
        --verbose \
        --file="$BACKUP_FILE" 2>&1 | tee -a "$BACKUP_DIR/backup.log"
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo ""
echo "[OK] Backup completed: $BACKUP_FILE ($BACKUP_SIZE)"

# ── Generate SHA256 checksum ────────────────────────────────────────────────
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
sha256sum "$BACKUP_FILE" > "$CHECKSUM_FILE"
echo "[OK] Checksum: $CHECKSUM_FILE"

# ── Optional: optional secondary compression ────────────────────────────────
if [ "$COMPRESS" = "gzip" ] && command -v gzip &> /dev/null; then
    if [ "${BACKUP_KEEP_DUMP:-0}" != "1" ]; then
        gzip -f "$BACKUP_FILE"
        echo "[OK] Compressed to ${BACKUP_FILE}.gz"
    fi
fi

# ── Retention: delete backups older than N days ──────────────────────────────
echo ""
echo "Pruning backups older than ${BACKUP_RETENTION_DAYS} days..."
DELETED=$(find "$BACKUP_DIR" -name "erp_backup_*.dump*" -mtime +"$BACKUP_RETENTION_DAYS" -type f -print -delete | wc -l)
echo "[OK] Pruned ${DELETED} old backup(s)"

# ── Disk usage report ────────────────────────────────────────────────────────
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "erp_backup_*.dump*" -type f | wc -l)
echo "[OK] Backup dir size: ${TOTAL_SIZE} (${BACKUP_COUNT} file(s))"

# ── Verify backup integrity ─────────────────────────────────────────────────
echo ""
echo "Verifying backup integrity..."
if pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1; then
    echo "[OK] Backup integrity verified"
else
    echo "[WARN] Backup integrity check FAILED — investigate immediately"
    exit 1
fi

echo ""
echo "============================================================"
echo "  Backup complete: ${BACKUP_FILE}"
echo "============================================================"
exit 0
