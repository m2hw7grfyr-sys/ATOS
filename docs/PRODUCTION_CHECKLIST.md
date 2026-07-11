# ATOS Production Checklist

## Environment

- [ ] `.env.production` created from `.env.production.example`
- [ ] `APP_ENV=production`
- [ ] `DEBUG=false`
- [ ] No development default password remains
- [ ] `ADMIN_DEFAULT_PASSWORD_CHANGED=true`

## Docker

- [ ] `docker-compose.prod.yml` reviewed
- [ ] `pgadmin` disabled in production
- [ ] Backend, frontend, worker, scheduler, postgres, redis, nginx enabled

## Database

- [ ] PostgreSQL used
- [ ] Migration from empty database tested
- [ ] Existing database upgrade tested
- [ ] Seed idempotency tested

## Redis

- [ ] Redis AOF enabled
- [ ] Redis RDB enabled
- [ ] Queue recovery strategy understood

## Nginx

- [ ] Domain updated in `infra/nginx/atos.prod.conf`
- [ ] API route `/api/` configured
- [ ] WebSocket upgrade headers enabled

## HTTPS

- [ ] Cloudflare Tunnel enabled, or
- [ ] Nginx + Certbot certificate installed
- [ ] No naked public HTTP API

## Backup

- [ ] `scripts/backup/postgres_backup.sh` tested
- [ ] `scripts/backup/storage_backup.sh` tested
- [ ] Backup directory monitored

## Restore Test

- [ ] PostgreSQL restore tested on staging
- [ ] Storage restore tested on staging
- [ ] Smoke test passed after restore

## Worker Token

- [ ] `WORKER_API_TOKEN` configured
- [ ] Token stored only in env
- [ ] Rotation procedure documented

## Admin Password

- [ ] Default admin password changed
- [ ] Admin access protected by reverse proxy / Cloudflare / VPN

## CORS

- [ ] `CORS_ORIGINS` only includes production domain
- [ ] No wildcard CORS in production

## Health Check

- [ ] `/health` works
- [ ] `/ready` works
- [ ] `/live` works
- [ ] `/metrics` works

## Monitoring

- [ ] Dashboard alert count visible
- [ ] Worker online/offline visible
- [ ] Queue length visible
- [ ] Submission failure rate visible

## Emergency Stop

- [ ] Emergency Stop tested
- [ ] AUTO_ASSISTED tasks return to manual
- [ ] Audit log written

## Operator Manual

- [ ] Operator manual reviewed
- [ ] Administrator manual reviewed
- [ ] Known limitations reviewed
