#!/bin/bash
# ERP Builder Protocol — PostgreSQL Backup
# Run via cron: 0 2 * * * /path/to/scripts/db_backup.sh

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_URL="${DATABASE_URL:-postgresql://user:pass@localhost:5432/erp}"

mkdir -p "$BACKUP_DIR"

pg_dump "$DB_URL" \
  --format=custom \
  --file="$BACKUP_DIR/erp_backup_${TIMESTAMP}.dump" \
  --verbose

ls -t "$BACKUP_DIR"/erp_backup_*.dump | tail -n +15 | xargs -r rm

echo "✅ Backup completed: $BACKUP_DIR/erp_backup_${TIMESTAMP}.dump"
