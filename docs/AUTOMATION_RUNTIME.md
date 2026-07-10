# ATOS Automation Runtime

Version: Sprint 08

Status: Implemented Scaffold

---

## Purpose

Automation Runtime allows ATOS to run continuously with multiple workers.

It manages:

- Worker Pool
- Task Queue
- Worker Claim
- Distributed Lock
- Retry
- Recovery
- Heartbeat
- Monitoring
- Alerts

Execution still owns the execution task lifecycle.

Automation Runtime owns long-running task distribution.

---

## Runtime Flow

```text
Scheduler
-> Execution Queue
-> Automation Runtime
-> Worker Claim
-> Execution Runtime
-> Result
```

---

## Worker Pool

Workers are stored in `worker_nodes`.

Important fields:

- worker_type
- capabilities
- max_concurrent_tasks
- current_tasks
- priority
- region
- health_score
- failure_rate
- task_success_rate
- last_heartbeat

Workers can represent:

- Local development worker
- Linux worker
- Windows AI workstation
- Browser worker
- AI worker

---

## Capability Scheduling

Each task can define a required capability.

Examples:

- BROWSER
- AI
- TGE
- PLAYWRIGHT
- EMBEDDING

Automation Runtime only assigns a task to a worker that declares the required capability.

---

## Task Claim

A worker claims one task at a time through Automation Runtime.

Claim writes:

- execution_tasks.worker_node_id
- execution_tasks.claimed_by_worker
- execution_tasks.claimed_at
- execution_tasks.lock_uuid
- execution_queue.worker_node_id
- execution_queue.lock_uuid

---

## Distributed Lock

Sprint 08 implements database fallback locks in `task_locks`.

Redis locks are reserved for future production mode.

The database lock prevents the same execution task from being claimed twice.

---

## Retry Engine

Execution task retry fields:

- retry_count
- max_retry
- retry_delay_seconds
- retry_strategy
- next_retry_at

Supported MVP strategy:

- EXPONENTIAL
- FIXED

When a task fails but retry is available:

```text
FAILED
-> RETRY_PENDING
-> QUEUED / CLAIMED
```

---

## Failure Recovery

Worker heartbeat timeout defaults to 90 seconds in Automation Runtime.

When a worker is lost:

```text
RUNNING
-> WORKER_LOST
-> RETRY_PENDING
```

The task is not deleted.

The lock is released.

The queue remains recoverable.

---

## Monitoring

Runtime metrics include:

- Queue length
- Online workers
- Offline workers
- Running tasks
- Failed tasks
- Retry pending
- Worker lost
- Failure rate
- Throughput

Alerts include:

- Worker Offline
- Queue Too Long
- Failure Rate High
- AI Provider Error

---

## API

Automation endpoints:

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

## Scaling

Future scaling path:

```text
Linux Server
-> PostgreSQL / Redis
-> Multiple Windows Workers
-> Capability Scheduling
-> Browser Runtime
-> Execution Result
```

Workers can be added without changing business modules.

The server assigns tasks according to capability, priority, capacity, and health.
