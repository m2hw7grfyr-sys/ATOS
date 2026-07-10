# Sprint 01: Business Flow Integration

## Sprint Goal

Connect the first real ATOS business flow:

```text
Data Source -> Post Pool -> AI Workspace -> Scheduler
```

Execution remains non-executing in this sprint.

## Issue List

- Issue-0101 Business Pipeline
- Issue-0102 Post Status
- Issue-0103 Pipeline API
- Issue-0104 Dashboard
- Issue-0105 Post Pool
- Issue-0106 AI Workspace
- Issue-0107 Scheduler
- Issue-0108 Business Event
- Issue-0109 Audit Log
- Issue-0110 Timeline
- Issue-0111 Notification
- Issue-0112 Search
- Issue-0113 Filter Preset
- Issue-0114 Pagination
- Issue-0115 Statistics
- Issue-0116 Seed
- Issue-0117 README
- Issue-0118 Sprint Report

## Completed

- Added `BusinessPipelineService` as the single orchestration entrypoint for post preparation, AI generation, approval, rejection, archive, and scheduling.
- Added local `EventBus` persistence through `business_events`.
- Added `post_timelines` to show status transitions on post detail.
- Added audit writes for approve, reject, archive, and schedule actions.
- Added `POST /pipeline/run`, `POST /pipeline/post/{id}`, `POST /pipeline/batch`, and `GET /pipeline/status`.
- Unified post lifecycle around `NEW`, `NORMALIZED`, `READY_FOR_AI`, `ANALYZING`, `AI_COMPLETED`, `WAITING_REVIEW`, `APPROVED`, `SCHEDULED`, and `ARCHIVED`.
- Scheduler tasks now preserve `post_id`, `reply_id`, `ai_task_id`, and `source`.
- Dashboard now shows Pipeline Overview metrics.
- Post Pool supports search, filters, pagination, batch Analyze, Approve, Reject, Archive, Send To Scheduler, Raw JSON, and Timeline.
- AI Workspace supports batch Generate, Approve, and Reject.
- Seed data now includes a complete demo flow: 20 posts, 20 AI tasks, 10 approved replies, and 8 scheduled tasks.

## Acceptance

The following MVP flow is implemented:

```text
Data Source
  -> Post Pool
  -> AI Workspace
  -> Scheduler
```

Execution remains intentionally paused/non-executing.

## Known Issues

- Filter Preset has backend support; deeper UI management is still minimal.
- Notification is still lightweight page-level feedback, not a full toast center.
- BusinessPipelineService uses the existing mock/real AI provider pipeline; production scoring quality depends on provider configuration.
- Full Repository Pattern migration remains incremental from Sprint 00.

## Quality Check

To be updated after local validation:

```bash
make quality
```

## Commit Hash

See final response or `git log -1 --oneline`.

## Next Sprint

Sprint 02 can start after quality checks pass and Sprint 01 is pushed.
