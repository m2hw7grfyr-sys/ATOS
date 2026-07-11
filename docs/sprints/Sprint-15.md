# Sprint-15: Production Release Foundation

Milestone: Production Release Foundation

## Sprint Goal

Prepare ATOS for v1.0 production release readiness without adding new business features.

## Completed Issues

- Added environment separation examples for development, staging, and production.
- Added `VERSION`.
- Added production Docker Compose.
- Added production frontend Dockerfile.
- Added Nginx reverse proxy config.
- Added Redis persistence config.
- Added PostgreSQL backup and restore scripts.
- Added storage backup and restore scripts.
- Added health, readiness, liveness, and metrics endpoints.
- Added production logging file layout and logrotate config.
- Added production AUTO_ASSISTED guard checks.
- Added production smoke test script.
- Added GitHub Actions production check.
- Added production deployment documentation.
- Added administrator manual.
- Added production checklist.
- Added v1.0 draft release notes.
- Added known limitations.
- Updated operator manual.

## Production Architecture

Production stack:

```text
Nginx / HTTPS
↓
Frontend + Backend API
↓
PostgreSQL + Redis
↓
Worker + Scheduler
↓
Browser Runtime / Platform Runtime
```

## Deployment Summary

Use:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

HTTPS options:

- Cloudflare Tunnel
- Nginx + Certbot

## Security Summary

Production guard checks:

- debug disabled
- CORS restricted
- worker token configured
- secure cookie mode
- admin default password changed
- AUTO_ASSISTED audit / screenshot / verification enabled

## Backup Summary

Scripts:

- `scripts/backup/postgres_backup.sh`
- `scripts/backup/postgres_restore.sh`
- `scripts/backup/storage_backup.sh`
- `scripts/backup/storage_restore.sh`

## Monitoring Summary

Endpoints:

- `/health`
- `/ready`
- `/live`
- `/metrics`

Dashboard shows worker, automation, submission, template, and alert metrics.

## Known Issues

- Full internal user authentication is not yet implemented.
- S3 / Google Drive backup adapters are reserved.
- Real worker service operation must be validated on the Windows workstation.
- Real platform selectors require live account testing.

## v1.0 Readiness

ATOS is now production-release-foundation ready, pending:

- production auth hardening
- staging restore test
- real worker deployment rehearsal
- domain / HTTPS setup
- final v1.0 release sign-off
