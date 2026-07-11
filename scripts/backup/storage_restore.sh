#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/backup/storage_restore.sh <storage.tar.gz>"
  exit 2
fi

BACKUP_FILE="$1"
RESTORE_ROOT="${RESTORE_ROOT:-.}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 2
fi

tar -xzf "$BACKUP_FILE" -C "$RESTORE_ROOT"
echo "Storage restore completed into $RESTORE_ROOT"
