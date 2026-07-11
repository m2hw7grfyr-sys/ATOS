#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/backup/postgres_restore.sh <backup.sql.gz>"
  exit 2
fi

BACKUP_FILE="$1"
DATABASE_URL_VALUE="${DATABASE_URL:-}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER_VALUE="${POSTGRES_USER:-atos}"
POSTGRES_DB_VALUE="${POSTGRES_DB:-atos}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 2
fi

echo "Restoring PostgreSQL from $BACKUP_FILE"
if [ -n "$DATABASE_URL_VALUE" ]; then
  gunzip -c "$BACKUP_FILE" | psql "$DATABASE_URL_VALUE"
else
  gunzip -c "$BACKUP_FILE" | psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER_VALUE" "$POSTGRES_DB_VALUE"
fi
echo "PostgreSQL restore completed"
