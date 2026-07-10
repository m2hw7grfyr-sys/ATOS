# Sprint-08: Automation Runtime

Milestone: Automation Runtime

Status: Completed

---

## Sprint Goal

Build the long-running automation foundation for ATOS.

Target flow:

```text
Linux Server
-> Multiple Workers
-> Task Queue
-> Worker Claim
-> Execution
-> Result
```

Worker loss must not lose tasks.

---

## Completed

- Added `AutomationRuntime`.
- Upgraded `worker_nodes` for Worker Pool:
  - worker_type
  - capabilities
  - max_concurrent_tasks
  - current_tasks
  - priority
  - region
  - health_score
  - failure_rate
  - task_success_rate
- Added worker registration and heartbeat through Automation Runtime.
- Added 90-second stale worker recovery.
- Added task claim by worker.
- Added database fallback task lock.
- Added priority queue support.
- Added worker concurrency control.
- Added retry engine fields and retry pending flow.
- Added worker lost recovery flow.
- Added runtime metrics.
- Added worker log aggregation fields.
- Added system alerts.
- Added Worker Center UI.
- Added Dashboard automation overview.

---

## API

Added:

- GET `/automation/runtime`
- GET `/automation/workers`
- POST `/automation/workers/register`
- POST `/automation/workers/heartbeat`
- POST `/automation/claim`
- POST `/automation/tasks/{task_id}/start`
- POST `/automation/tasks/{task_id}/complete`
- POST `/automation/tasks/{task_id}/retry`
- POST `/automation/recover`
- GET `/automation/queue`
- GET `/automation/locks`
- GET `/automation/metrics`
- GET `/automation/alerts`
- GET `/automation/logs`

---

## UI

Added:

- Worker Center
- Automation Runtime overview
- Worker Pool table
- Execution Queue table
- Alerts table
- Runtime Metrics
- Claim Next action

---

## State Flow

```text
QUEUED
-> CLAIMED
-> RUNNING
-> SUCCESS
```

Failure recovery:

```text
RUNNING
-> WORKER_LOST
-> RETRY_PENDING
```

---

## Tests

Covered:

- Worker registration
- Capability-based claim
- Concurrency control
- Database task lock
- Worker lost recovery
- Retry pending state

Executed:

- `PYTHONPATH=backend .venv/bin/python -m unittest backend.tests.test_automation_runtime`
- `PYTHONPATH=backend .venv/bin/python -m unittest discover backend/tests`
- `DATABASE_URL=sqlite:////private/tmp/atos_sprint08_migration.db PYTHONPATH=. ../.venv/bin/alembic -c alembic.ini upgrade head`
- `DATABASE_URL=sqlite:////private/tmp/atos_sprint08_migration.db PYTHONPATH=backend .venv/bin/python backend/scripts/seed_data.py`
- `PATH=/Users/zhangkaikai/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH /Users/zhangkaikai/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/pnpm run build`

---

## Known Issues

- Redis distributed lock is not implemented yet; Sprint 08 uses database fallback lock.
- Worker execution is still scaffold-level and does not run real browser automation.
- Remote worker authentication is still inherited from Sprint 06 token mode.

---

## Commit Hash

See final Git commit hash reported after commit.

---

## Next Sprint

Recommended next sprint:

- Real remote worker process loop
- Redis lock adapter
- Worker task pull API with token auth
- Runtime event stream
- Advanced queue fairness
