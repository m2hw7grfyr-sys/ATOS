# ATOS GPU Worker Phase 03 Report

Status: Partially complete locally

## Goal

Implement the minimum communication loop:

Windows Main -> AI generation task -> GPU Worker lease -> Ollama generation -> GPU Worker result callback -> Main Dashboard.

## Completed Locally

- Added GPU Worker API key configuration.
- Added automatic `atos_gpu_*` key generation when `GPU_WORKER_API_KEY` is empty.
- Added `gpu_worker_statuses` table.
- Added `gpu_generation_tasks` table.
- Added Alembic migration `0025_gpu_worker_generation_queue`.
- Added GPU Worker bearer-token authentication.
- Added task lease, started, complete, and failed endpoints.
- Added idempotent complete handling.
- Added expired lease requeue handling.
- Added Worker Center GPU runtime panel.
- Added test task creation from the Dashboard.
- Added local GPU Worker project under `workers/gpu`.
- Added non-stream Ollama generation client.
- Added worker heartbeat thread so generation does not block heartbeat.
- Added supervisor config templates with `autostart=false`.
- Updated `.env.example`.
- Updated README.

## Main API

Worker-authenticated endpoints:

```text
POST /api/gpu-worker/heartbeat
POST /api/gpu-worker/tasks/lease
POST /api/gpu-worker/tasks/{task_id}/started
POST /api/gpu-worker/tasks/{task_id}/complete
POST /api/gpu-worker/tasks/{task_id}/failed
```

Dashboard endpoints:

```text
GET  /api/gpu-worker/dashboard
POST /api/gpu-worker/tasks
GET  /api/gpu-worker/config
```

## Worker Workflow

```text
Start Worker
  ↓
Read /workspace/config/gpu-worker.env
  ↓
Heartbeat loop
  ↓
Lease queued task
  ↓
Mark started
  ↓
Call Ollama /api/generate
  ↓
Complete or failed callback
  ↓
Poll again
```

## Tests Run

```text
../.venv/bin/python -m unittest tests.test_gpu_worker -v
python3 -m unittest workers.gpu.tests.test_worker_runner -v
PYTHONPYCACHEPREFIX=/tmp/atos-pycache ../.venv/bin/python -m compileall app tests/test_gpu_worker.py
PYTHONPYCACHEPREFIX=/tmp/atos-pycache python3 -m compileall workers/gpu
../.venv/bin/python -m alembic upgrade head
PATH=/Users/zhangkaikai/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:/Users/zhangkaikai/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin:$PATH pnpm run build
```

Verified:

- Missing token returns unauthorized at auth dependency level.
- Wrong token returns unauthorized at auth dependency level.
- Heartbeat creates and updates worker status.
- Stale worker is marked offline.
- Empty queue returns no task.
- A queued task is not claimed twice.
- Complete writes result.
- Repeated complete is idempotent.
- Failed task records error.
- Expired lease can be reclaimed.
- Worker reports Ollama failure without exiting.
- Backend migration reaches head.
- Frontend build succeeds.

## Remote Vast Work Not Completed

Remote deployment was not completed because the SSH command was rejected by the Codex escalation system due to usage quota:

```text
Automatic approval review failed: You've hit your usage limit.
```

Pending remote actions:

- Sync `workers/gpu` to `/workspace/atos-gpu-worker`.
- Copy `workers/gpu/config/gpu-worker.env.example` to `/workspace/config/gpu-worker.env`.
- Update `/workspace/config/supervisor/atos-gpu-worker.conf`.
- Link supervisor configs into the active supervisor include directory if needed.
- Run `supervisorctl reread` and `supervisorctl update`.
- Keep both programs stopped until manually started.
- List `/workspace/backups`.
- Remove only installer/download leftovers from `/workspace/backups`.
- Report freed disk space.

## Config Needed on Vast

```env
MAIN_URL=http://<windows-main-host>:8080
GPU_WORKER_API_KEY=<copy-from-dashboard>
WORKER_NAME=vast-gpu-worker-01
WORKER_TYPE=gpu
OLLAMA_URL=http://127.0.0.1:11434
MODEL_NAME=llama3.1:8b
HEARTBEAT_INTERVAL_SECONDS=10
POLL_INTERVAL_SECONDS=5
```

## Supervisor Start Method

Manual only:

```bash
supervisorctl start ollama
supervisorctl start atos-gpu-worker
```

No autostart, no Vast auto-stop, and no browser automation are included in this phase.

## Next Stage Suggestions

- Complete remote sync when SSH execution is available.
- Test Main URL reachability from Vast to Windows Main.
- Run one end-to-end task through Ollama.
- Add a production-safe tunnel or reverse connection plan.
- Only after the loop is stable, design Vast start/stop automation.
