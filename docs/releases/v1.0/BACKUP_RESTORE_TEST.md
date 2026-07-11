# Backup Restore Test

Version: 1.0.0-rc.1

## Scripts

- `scripts/backup/postgres_backup.sh`
- `scripts/backup/postgres_restore.sh`
- `scripts/backup/storage_backup.sh`
- `scripts/backup/storage_restore.sh`

## Local Validation

Shell syntax check passed for all backup and restore scripts.

## Not Executed Locally

Actual PostgreSQL backup/restore and storage restore were not executed locally because the current validation host does not have the production Docker/PostgreSQL stack running.

## Required Production Validation

Run a backup and restore on staging before promoting v1.0 to final release.

