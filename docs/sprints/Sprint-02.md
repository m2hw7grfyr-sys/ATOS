# Sprint 02: Execution Ready

## Sprint Goal

Build the real Execution Engine foundation without browser automation.

## Milestone

Execution Ready.

## Issue List

- Issue-0201 Execution Runtime
- Issue-0202 Execution Queue
- Issue-0203 Worker
- Issue-0204 Worker Registration
- Issue-0205 Heartbeat
- Issue-0206 Execution Status
- Issue-0207 Execution Logs
- Issue-0208 Execution Timeline
- Issue-0209 Replay Index
- Issue-0210 Execution Dashboard
- Issue-0211 Retry
- Issue-0212 Cancel
- Issue-0213 Manual Resume
- Issue-0214 API
- Issue-0215 Seed
- Issue-0216 README
- Issue-0217 Sprint Report

## Completed

- Added `ExecutionRuntime` with local worker registration, heartbeat, queue claim, run, retry, cancel, and manual resume.
- Added `worker_nodes` for Worker Registration and heartbeat visibility.
- Added `execution_queue` so Scheduler only pushes and Execution consumes.
- Added `replay_indexes` as a Replay structure placeholder without screenshots.
- Expanded Execution lifecycle to `NEW`, `QUEUED`, `CLAIMED`, `RUNNING`, `WAITING_MANUAL`, `SUCCESS`, `FAILED`, `CANCELLED`.
- Scheduler now pushes tasks into Execution Queue instead of directly executing browser-related actions.
- Added Runtime APIs: `/execution/runtime`, `/execution/workers`, `/execution/queue`, `/execution/claim-next`, `/execution/retry`, `/execution/cancel`, `/execution/tasks/{id}/run-runtime`, `/execution/tasks/{id}/resume`.
- Dashboard now exposes Execution Queue, Workers, Running, Success, and Failed metrics.
- Execution page now shows runtime widgets, worker heartbeat, queue status, retry count, and runtime actions.
- Seed now creates 30 Execution demo tasks: 10 Running, 10 Waiting Manual, and 10 Success.

## Acceptance

Implemented:

```text
Scheduler -> Execution Queue -> Worker -> Execution Runtime -> Dashboard
```

Still intentionally not implemented:

- Browser automation
- Playwright execution
- TGE attach/start
- Automatic submit/comment actions

## Known Issues

- Worker is local-only; remote worker registration is represented by schema and API-ready structures.
- Heartbeat is updated when runtime APIs are called, not by a daemon process in this sprint.
- Replay Index exists as metadata only; screenshots and HTML artifacts remain future work.
- Existing legacy execution action endpoints remain for compatibility, but Sprint 02 runtime actions are the preferred path.

## Quality Check

Passed:

```bash
make quality
```

Validated:

- Backend compile check
- Backend unit tests
- Frontend TypeScript lint
- Frontend production build
- Alembic migration
- Seed run
- Repeated seed run

Not executed:

- Live localhost API smoke test. Starting a temporary uvicorn port requires local bind approval in this sandbox, and the approval request was blocked by the current usage limit. Backend unit tests and migration/seed checks passed.

## Commit Hash

See final response or `git log -1 --oneline`.

## Next Sprint

Sprint 03 can start after this sprint is pushed.
