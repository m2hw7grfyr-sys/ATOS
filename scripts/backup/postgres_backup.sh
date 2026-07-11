#!/usr/bin/env sh
set -eu

BACKUP_ROOT="${BACKUP_ROOT:-storage/backups/postgres}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DATABASE_URL_VALUE="${DATABASE_URL:-}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER_VALUE="${POSTGRES_USER:-atos}"
POSTGRES_DB_VALUE="${POSTGRES_DB:-atos}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

mkdir -p "$BACKUP_ROOT"
OUT="$BACKUP_ROOT/atos-postgres-$TIMESTAMP.sql.gz"

if [ -n "$DATABASE_URL_VALUE" ]; then
  pg_dump "$DATABASE_URL_VALUE" | gzip > "$OUT"
else
  pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER_VALUE" "$POSTGRES_DB_VALUE" | gzip > "$OUT"
fi

find "$BACKUP_ROOT" -name 'atos-postgres-*.sql.gz' -type f -mtime +"$RETENTION_DAYS" -delete
echo "PostgreSQL backup created: $OUT"
