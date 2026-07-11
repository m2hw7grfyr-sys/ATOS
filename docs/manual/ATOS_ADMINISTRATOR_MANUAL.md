# ATOS Administrator Manual

Status: Sprint 15

## 1. System Configuration

Administrators manage:

- Environment variables
- System Settings
- Scheduler defaults
- Platform rules
- Worker tokens
- Backup and restore
- AUTO_ASSISTED production guard

Production config must come from `.env.production`.

## 2. User Permissions

ATOS defines four roles:

- Administrator
- Operator
- Reviewer
- Viewer

Production policy:

- Administrator can manage all settings.
- Operator can run operational tasks.
- Reviewer can approve or reject content.
- Viewer is read-only.

Restricted areas:

- System Settings
- Worker Token
- AUTO_ASSISTED Global Switch
- Backup / Restore
- Security Settings

Until full user auth is connected, production deployments should enforce access through Cloudflare Access, VPN, or reverse-proxy authentication.

## 3. Worker Management

Workers must register with `WORKER_API_TOKEN`.

Token rules:

- Store only in environment variables.
- Rotate regularly.
- Disable leaked tokens immediately.
- Do not print tokens in logs.

Worker health is visible in Dashboard and `/health/worker`.

## 4. Platform Configuration

Platform Runtime controls adapters and capability checks.

Administrators can:

- Enable / disable platform adapters.
- Review platform health.
- Configure selectors.
- Check capabilities before execution.

## 5. AI Provider Configuration

AI providers are managed in System Settings.

Rules:

- API keys are masked in UI.
- API keys must not appear in logs.
- Mock provider must remain available for fallback.
- Production providers should be tested before traffic runs.

## 6. AUTO_ASSISTED Configuration

AUTO_ASSISTED requires:

- Global switch
- Platform switch
- Account switch
- Daily limit
- Time window
- Healthy worker
- Audit enabled
- Screenshot enabled
- Verification enabled

Production guard blocks AUTO_ASSISTED if required safety configuration is incomplete.

## 7. Backup And Restore

Database backup:

```bash
scripts/backup/postgres_backup.sh
```

Database restore:

```bash
scripts/backup/postgres_restore.sh <backup.sql.gz>
```

Storage backup:

```bash
scripts/backup/storage_backup.sh
```

Always stop backend, worker, and scheduler before database restore.

## 8. Log Review

Production logs live in:

```text
storage/logs/
```

Standard files:

- `backend.log`
- `worker.log`
- `scheduler.log`
- `execution.log`
- `submission.log`
- `ai.log`
- `browser.log`
- `error.log`

Rotation is documented in `infra/logrotate/atos.conf`.

## 9. Alert Handling

Default alert types:

- Worker Offline
- Queue Too Long
- AI Provider Error
- Submission Failure Rate High
- Database Backup Failed
- Redis Down
- Disk Usage High
- AUTO_ASSISTED Emergency Stop Triggered

Dashboard shows open alert count.

## 10. Production Deployment

Use:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

See:

```text
docs/DEPLOYMENT_PRODUCTION.md
```
