# ATOS Production Deployment

Status: Sprint 15

## Server Requirements

Recommended server:

- Linux VPS with Docker and Docker Compose
- 2 CPU / 4 GB RAM minimum for a small console
- 40 GB disk minimum
- Public domain routed through Cloudflare or Nginx + Certbot

Production should use:

- PostgreSQL
- Redis with persistence
- Nginx reverse proxy
- HTTPS only
- Worker token authentication
- Daily database backup

## Windows Worker Requirements

Windows AI Workstation should have:

- TGE or supported browser profile runtime
- Playwright dependencies
- Stable proxy and login session
- ATOS Worker installed as Windows Service
- Outbound HTTPS access to ATOS server

Do not expose Windows Worker ports directly to the public Internet.

## Environment Variables

Use `.env.production.example` as the template.

Required production replacements:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `WORKER_API_TOKEN`
- `CORS_ORIGINS`
- `PUBLIC_API_BASE_URL`
- `API_BASE_URL`
- `VITE_API_BASE_URL`
- `ADMIN_DEFAULT_PASSWORD_CHANGED=true`

Production must not use development default values.

## Docker Compose

Prepare:

```bash
cp .env.production.example .env.production
```

Edit `.env.production`, then start:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Services:

- `postgres`
- `redis`
- `backend`
- `frontend`
- `worker`
- `scheduler`
- `nginx`

`pgadmin` is intentionally excluded from production.

## Cloudflare Tunnel HTTPS

Recommended for small deployments:

1. Create a Cloudflare Tunnel.
2. Route `atos.example.com` to the Nginx service.
3. Keep server ports private where possible.
4. Use Cloudflare Access or firewall rules for admin routes.

Production API must be HTTPS.

## Nginx + Certbot HTTPS

The production compose file mounts:

- `infra/nginx/atos.prod.conf`
- `storage/certbot/www`
- `storage/certbot/conf`

Replace `atos.example.com` in `infra/nginx/atos.prod.conf` with your domain.

Use Certbot to provision certificates into `storage/certbot/conf`.

## Health Checks

Available endpoints:

- `GET /health`
- `GET /health/backend`
- `GET /health/database`
- `GET /health/redis`
- `GET /health/worker`
- `GET /health/scheduler`
- `GET /health/ai-runtime`
- `GET /health/browser-runtime`
- `GET /ready`
- `GET /live`
- `GET /metrics`

`/ready` should be used for dependency readiness.

`/live` should be used for process liveness.

## Database Backup

Manual backup:

```bash
scripts/backup/postgres_backup.sh
```

Default output:

```text
storage/backups/postgres/
```

Retention defaults:

- 7 daily
- 4 weekly
- 3 monthly

Current scripts implement local compressed backups and daily retention. Weekly/monthly retention adapters are reserved for future enhancement.

## Restore

Before restore:

```bash
docker compose -f docker-compose.prod.yml stop backend worker scheduler
```

Restore:

```bash
scripts/backup/postgres_restore.sh storage/backups/postgres/<backup>.sql.gz
```

Verify:

```bash
scripts/smoke_test.py
```

Restart:

```bash
docker compose -f docker-compose.prod.yml up -d backend worker scheduler
```

## Storage Backup

Manual storage backup:

```bash
scripts/backup/storage_backup.sh
```

Restore:

```bash
scripts/backup/storage_restore.sh storage/backups/storage/<backup>.tar.gz
```

Backed up:

- screenshots
- HTML snapshots
- exports
- local logs if included

Future adapters:

- Google Drive
- S3

## Redis Persistence

Production Redis uses:

```text
infra/redis/redis.prod.conf
```

Persistence:

- AOF enabled
- RDB snapshots enabled

If Redis restarts, database-backed task state remains the source of truth. Redis is treated as a runtime accelerator.

## Worker Setup

Worker registration requires:

- `WORKER_API_TOKEN`
- worker heartbeat
- capability declaration

Never print or commit worker tokens.

## Troubleshooting

Check logs:

```bash
ls storage/logs
```

Check health:

```bash
scripts/smoke_test.py
```

Check compose:

```bash
docker compose -f docker-compose.prod.yml ps
```

If AUTO_ASSISTED behaves unexpectedly, use Emergency Stop from System Settings or call:

```bash
POST /submission/emergency-stop
```
