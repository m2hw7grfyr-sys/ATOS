# ATOS Deployment Guide

Version: Sprint 06

Status: Foundation

## Goal

Sprint 06 establishes the remote access and long-running foundation for ATOS.

Supported topology:

```text
Operator Browser
  ↓ HTTPS
Cloudflare
  ↓ Tunnel
Linux VPS / ATOS Server
  ↓ HTTPS REST API
Windows AI Workstation / ATOS Worker
```

Production remote APIs must use HTTPS.

Do not expose ATOS backend or worker ports directly to the public internet.

## Architecture

ATOS supports three deployment modes:

- Local Development
- Linux VPS Server
- Windows Worker

Communication:

- HTTPS
- REST API
- Health Check
- Token authenticated Worker API

## Environment

Required server values:

```env
PUBLIC_API_BASE_URL=https://atos.example.com
WORKER_API_TOKEN=change-this-token
WORKER_TOKEN_VERSION=v1
WORKER_HEARTBEAT_TIMEOUT_SECONDS=90
LOG_DIR=storage/logs
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=7
```

Required Windows Worker values:

```powershell
$env:ATOS_SERVER_URL = "https://atos.example.com"
$env:WORKER_API_TOKEN = "change-this-token"
```

Rotate `WORKER_API_TOKEN` by updating the server environment and reinstalling or restarting the Windows Worker with the new token.

## Cloudflare Tunnel

Install `cloudflared` on the server.

Create tunnel:

```bash
cloudflared tunnel create atos-server
```

Route domain:

```bash
cloudflared tunnel route dns atos-server atos.example.com
```

Example config:

```yaml
tunnel: atos-server
credentials-file: /etc/cloudflared/atos-server.json

ingress:
  - hostname: atos.example.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

Run tunnel:

```bash
cloudflared tunnel run atos-server
```

Install as service:

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl restart cloudflared
```

## Custom Domain

Recommended domains:

```text
atos.example.com
worker.example.com
```

Use Cloudflare DNS with proxied records. Cloudflare Tunnel enables HTTPS automatically.

## HTTPS Rule

Production:

- `PUBLIC_API_BASE_URL` must start with `https://`.
- Worker must call server through HTTPS.
- Do not publish `http://host:8000` directly.

Local development may use:

```text
http://127.0.0.1:8000
```

## Windows Worker Service

Scripts live in:

```text
scripts/windows/
```

Install:

```powershell
$env:ATOS_SERVER_URL = "https://atos.example.com"
$env:WORKER_API_TOKEN = "change-this-token"
powershell -ExecutionPolicy Bypass -File scripts/windows/install-worker.ps1
```

Start:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/start-worker.ps1
```

Stop:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/stop-worker.ps1
```

Health check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/health-check.ps1
```

Service name:

```text
ATOS Worker
```

The service starts automatically after Windows reboot.

## Worker API

All Worker API calls require:

```http
X-Worker-Token: <WORKER_API_TOKEN>
```

Endpoints:

```text
GET  /worker/health
POST /workers/register
POST /workers/heartbeat
GET  /workers
GET  /workers/{id}
POST /workers/{id}/restart
GET  /workers/{id}/logs
```

Heartbeat payload:

```json
{
  "worker_id": "windows-ai-01",
  "timestamp": "2026-07-10T00:00:00Z",
  "cpu": 20.5,
  "memory": 61.2,
  "gpu": 12.1,
  "runtime_status": "READY",
  "capabilities": {
    "AI": true,
    "Browser": true,
    "TGE": true,
    "Playwright": true,
    "Embedding": true
  }
}
```

## Auto Reconnect

The Windows Worker script retries registration and heartbeat with backoff.

Recommended backoff:

```text
5s
15s
30s
60s
```

## Log Management

Server logs:

```text
storage/logs/atos-application.log
```

Worker logs:

```text
C:\ATOS\worker\logs\worker-error.log
```

Log rotation:

- Server log rotates by size.
- Default max size: 10 MB.
- Default backups: 7.
- Worker API logs are indexed in `worker_logs`.

## Dashboard

Dashboard summary includes:

- Worker Online
- Worker Offline
- Average CPU
- Average Memory
- Average GPU
- Running Tasks

## Troubleshooting

Worker is not online:

1. Check `WORKER_API_TOKEN` on server and worker.
2. Run `scripts/windows/health-check.ps1`.
3. Check Cloudflare Tunnel status.
4. Check `storage/logs/atos-application.log`.
5. Check `C:\ATOS\worker\logs\worker-error.log`.

401 invalid worker token:

- Rotate and reapply `WORKER_API_TOKEN`.
- Restart `ATOS Worker`.

503 token not configured:

- Set `WORKER_API_TOKEN` on the server.
- Restart backend.

HTTP in production:

- Move traffic behind Cloudflare Tunnel.
- Set `PUBLIC_API_BASE_URL=https://...`.
