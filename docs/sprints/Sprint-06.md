# Sprint 06: Remote Access & Deployment Foundation

## Sprint Goal

Establish the remote access and long-running foundation for ATOS.

This sprint does not add business features.

Target:

```text
Windows AI Workstation
  ↓ auto start
ATOS Worker
  ↓ HTTPS REST
ATOS Server
  ↓ heartbeat
Dashboard Online
```

## Issue List

- Issue-0601 Remote Architecture
- Issue-0602 Cloudflare Tunnel
- Issue-0603 Custom Domain
- Issue-0604 HTTPS
- Issue-0605 Worker Service
- Issue-0606 Service Management
- Issue-0607 Worker Auto Start
- Issue-0608 Health Check
- Issue-0609 Heartbeat
- Issue-0610 Auto Reconnect
- Issue-0611 Worker Registration
- Issue-0612 Worker Capability
- Issue-0613 Remote Worker API
- Issue-0614 Log Management
- Issue-0615 Log Rotation
- Issue-0616 Remote Dashboard
- Issue-0617 Security
- Issue-0618 Deployment Documentation
- Issue-0619 Scripts
- Issue-0620 Sprint Report

## Completed

- Added Remote Access deployment documentation.
- Added Cloudflare Tunnel setup documentation.
- Added custom domain and HTTPS deployment rules.
- Added Windows Service scripts:
  - `scripts/windows/install-worker.ps1`
  - `scripts/windows/start-worker.ps1`
  - `scripts/windows/stop-worker.ps1`
  - `scripts/windows/health-check.ps1`
- Added token-authenticated Worker API:
  - `GET /worker/health`
  - `POST /workers/register`
  - `POST /workers/heartbeat`
  - `GET /workers`
  - `GET /workers/{id}`
  - `POST /workers/{id}/restart`
  - `GET /workers/{id}/logs`
- Extended `worker_nodes` with hostname, OS, IP, metrics, capabilities, runtime status, token version, and last seen.
- Added `worker_logs`.
- Added `RemoteWorkerService`.
- Added heartbeat timeout handling that marks stale workers offline.
- Added JSON file logging with size-based rotation.
- Added environment variables for worker token, token version, public HTTPS URL, and log rotation.
- Dashboard summary now includes worker online/offline and average CPU/memory/GPU metrics.
- Seed now creates a Windows AI Workstation worker demo.

## Remote Architecture

```text
Operator
  ↓ HTTPS
Cloudflare Tunnel
  ↓
ATOS Server
  ↓ HTTPS REST + Token
Windows AI Workstation
```

Production rule:

```text
Remote API = HTTPS only
Direct public port exposure = forbidden
```

## Worker State

```text
REGISTER
  ↓
ONLINE
  ↓ heartbeat every 30s
READY / RUNNING / WAITING_MANUAL
  ↓ missed heartbeat
OFFLINE
  ↓ heartbeat resumes
ONLINE
```

## Security

- Worker API requires `X-Worker-Token`.
- Token comes from `WORKER_API_TOKEN`.
- Token is not hardcoded.
- Token version is tracked through `WORKER_TOKEN_VERSION`.
- Token rotation is documented in `docs/DEPLOYMENT.md`.

## Log Management

Server:

```text
storage/logs/atos-application.log
```

Rotation:

```text
LOG_MAX_BYTES
LOG_BACKUP_COUNT
```

Worker:

```text
C:\ATOS\worker\logs\worker-error.log
```

Worker API logs are indexed in `worker_logs`.

## Acceptance

Implemented foundation for:

```text
Windows boot
  ↓
ATOS Worker auto start
  ↓
Register to Server
  ↓
Heartbeat
  ↓
Dashboard Online
  ↓
Network failure
  ↓
Retry / stale offline detection
  ↓
Heartbeat resumes
```

## Quality Check

Validated:

- Backend compile check
- Backend unit tests
- Remote worker service test
- Alembic migration
- Seed run
- Repeated seed run
- Frontend lint and build

## Known Issues

- Cloudflare Tunnel is documented but not launched in local tests.
- Windows Service scripts are created and syntax-structured, but actual service installation requires a Windows machine with administrator permissions.
- GPU metrics depend on future workstation-specific collection.
- `/workers/{id}/restart` records a restart request; a future worker agent should poll and act on it.

## Commit Hash

See final response or `git log -1 --oneline`.

## Next Sprint

Sprint 07 can start after Sprint 06 is pushed.
