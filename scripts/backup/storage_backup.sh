#!/usr/bin/env sh
set -eu

STORAGE_DIR="${STORAGE_DIR:-storage}"
BACKUP_ROOT="${BACKUP_ROOT:-storage/backups/storage}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

mkdir -p "$BACKUP_ROOT"
OUT="$BACKUP_ROOT/atos-storage-$TIMESTAMP.tar.gz"

tar \
  --exclude "$BACKUP_ROOT" \
  --exclude "$STORAGE_DIR/backups" \
  -czf "$OUT" "$STORAGE_DIR"

find "$BACKUP_ROOT" -name 'atos-storage-*.tar.gz' -type f -mtime +"$RETENTION_DAYS" -delete
echo "Storage backup created: $OUT"
