# Sprint 05: Semi-Auto Reply Pipeline

## Sprint Goal

Connect the complete semi-auto reply workflow:

```text
Post Pool
  ↓
AI Runtime
  ↓
Reply Review
  ↓
Scheduler Runtime
  ↓
Execution Runtime
  ↓
Browser Runtime
  ↓
Platform Adapter
  ↓
Fill Reply
  ↓
WAITING_MANUAL
  ↓
Human Confirm
  ↓
Execution Complete
```

Default execution mode is `SEMI_AUTO`.

`AUTO_ASSISTED` and `FULL_AUTO` are reserved as configuration values only.

## Issue List

- Issue-0501 Execution Mode
- Issue-0502 Reply Task
- Issue-0503 Reply Pipeline Service
- Issue-0504 AI Reply Approval
- Issue-0505 Scheduler Integration
- Issue-0506 Execution Integration
- Issue-0507 Execution Payload
- Issue-0508 Platform Adapter
- Issue-0509 Reddit Adapter
- Issue-0510 Browser Runtime Integration
- Issue-0511 WAITING_MANUAL
- Issue-0512 Manual Confirm
- Issue-0513 Close Tab
- Issue-0514 Replay
- Issue-0515 Execution UI
- Issue-0516 Dashboard
- Issue-0517 Statistics
- Issue-0518 Audit
- Issue-0519 Mock Mode
- Issue-0520 Sprint Report

## Completed

- Added `reply_tasks`.
- Added `execution_mode` with `SEMI_AUTO`, `AUTO_ASSISTED`, and `FULL_AUTO`.
- Added `ReplyPipelineService` as the orchestration boundary for reply task creation, approval, scheduling, execution preparation, and confirmation.
- AI approval now creates a Reply Task.
- Scheduler tasks can link to Reply Tasks through `reply_task_id`.
- Execution tasks can link to Reply Tasks through `reply_task_id`.
- Execution payload now carries `task_type`, `platform`, `url`, `account_id`, `tge_profile_id`, `reply_content`, `execution_mode`, and `metadata`.
- Added `/reply-tasks` APIs for create, approve, schedule, prepare, and confirm.
- Extended `PlatformAdapter` with `open_post`, `fill_reply`, `detect_rate_limit`, and `detect_reply_success`.
- Added `RedditAdapter`.
- Reply preparation flows through Browser Runtime before Platform Adapter fill.
- Filled replies enter `WAITING_MANUAL`.
- Manual confirm updates Reply Task, Execution Task, Scheduler Task, account usage, and closes the current tab.
- Dashboard summary now includes Reply Pipeline funnel metrics.
- Mock Mode supports the full loop without TGE or Playwright.

## Status Machine

```text
CREATED
  ↓
APPROVED
  ↓
SCHEDULED
  ↓
EXECUTING
  ↓
WAITING_MANUAL
  ↓
SUBMITTED
  ↓
CONFIRMED
```

Failure path:

```text
CREATED / APPROVED / SCHEDULED / EXECUTING / WAITING_MANUAL
  ↓
FAILED
```

Cancel path:

```text
CREATED / APPROVED / SCHEDULED
  ↓
CANCELLED
```

## Acceptance Flow

Validated in backend tests:

```text
AI Reply
  ↓ approve
Reply Task
  ↓ schedule
Scheduler Task
  ↓ dispatch
Execution Task
  ↓ Browser Runtime
Browser Tab
  ↓ Platform Adapter
Reply Filled
  ↓
WAITING_MANUAL
  ↓ confirm
CONFIRMED
```

## Safety Boundary

Sprint 05 does not automatically submit comments.

ATOS fills the reply draft and waits for the operator to review and submit manually on the platform.

## Quality Check

Validated:

- Backend compile check
- Backend unit tests
- Semi-auto Reply Pipeline test
- Alembic migration
- Seed run
- Repeated seed run
- Frontend lint and build

## Known Issues

- Real DOM filling still depends on platform selector quality.
- Current Sprint keeps real Playwright/TGE actions behind existing Browser Runtime scaffold.
- Replay stores timeline and placeholder screenshot paths; richer visual replay remains future work.
- UI has Execution detail primitives, but a dedicated Reply Task detail screen is still a future enhancement.

## Commit Hash

See final response or `git log -1 --oneline`.

## Next Sprint

Sprint 06 can start after Sprint 05 is pushed.
