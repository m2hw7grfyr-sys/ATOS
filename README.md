# ATOS

ATOS is an AI Traffic Operating System local MVP.

The current repository focuses on a stable development foundation:

- FastAPI backend
- React / TypeScript frontend
- SQLite for local development
- PostgreSQL / Redis Docker scaffold
- Alembic migrations
- Idempotent seed data
- Unified API response format
- JSON request logging
- Configuration Service
- Human-in-the-loop execution model

ATOS does not automatically submit comments in the current MVP.

## Business Flow

Sprint 01 connects the first real business pipeline:

```text
Data Source
  ↓ normalize
Post Pool
  ↓ analyze / generate
AI Workspace
  ↓ approve
Scheduler
```

Execution still stays non-executing in this sprint. Scheduler can receive tasks, but browser automation is not triggered by the business pipeline.

Primary Pipeline APIs:

```text
POST /pipeline/run
POST /pipeline/post/{id}
POST /pipeline/batch
GET  /pipeline/status
```

Typical local flow:

```bash
# Analyze one post and create a draft for human review
curl -X POST http://127.0.0.1:8000/pipeline/post/1 \
  -H "Content-Type: application/json" \
  -d '{"action":"ANALYZE"}'

# Approve selected posts
curl -X POST http://127.0.0.1:8000/pipeline/batch \
  -H "Content-Type: application/json" \
  -d '{"post_ids":[1,2],"action":"APPROVE"}'

# Send approved posts to Scheduler
curl -X POST http://127.0.0.1:8000/pipeline/batch \
  -H "Content-Type: application/json" \
  -d '{"post_ids":[1,2],"action":"SEND_TO_SCHEDULER"}'
```

Post lifecycle:

```text
NEW → NORMALIZED → READY_FOR_AI → ANALYZING → AI_COMPLETED
→ WAITING_REVIEW → APPROVED → SCHEDULED → ARCHIVED
```

## Execution Runtime

Sprint 02 introduces the Execution Ready milestone:

```text
Scheduler
  ↓ push only
Execution Queue
  ↓ claim
Worker
  ↓ state transition
Execution Runtime
  ↓ metrics
Dashboard
```

This runtime does not open browsers and does not run Playwright/TGE automation.

Primary Execution Runtime APIs:

```text
GET  /execution/runtime
GET  /execution/workers
GET  /execution/tasks
GET  /execution/queue
POST /execution/claim-next
POST /execution/retry
POST /execution/cancel
POST /execution/tasks/{id}/run-runtime
POST /execution/tasks/{id}/resume
```

Execution lifecycle:

```text
NEW → QUEUED → CLAIMED → RUNNING → WAITING_MANUAL
→ SUCCESS
→ FAILED
→ CANCELLED
```

Retry re-queues the same task and does not create a duplicate task.

## Browser Runtime

Sprint 03 introduces Browser Runtime as the only interface between Execution and browsers:

```text
Execution
  ↓
Browser Runtime
  ↓
Browser Adapter
  ↓
Playwright Adapter / TGE Adapter / Mock Adapter
```

Execution must not call Playwright, TGE, AdsPower, Chrome, or other browser implementations directly.

Primary Browser Runtime APIs:

```text
GET  /browser/runtime
GET  /browser/sessions
GET  /browser/tabs
POST /browser/open
POST /browser/close
POST /browser/recover
```

Browser Runtime manages:

- Session lifecycle
- Tab lifecycle
- Session heartbeat
- Session recovery
- Replay index metadata

Sprint 03 uses mock-safe adapters by default. It does not require real browser files, screenshots, or networked browser automation.

## AI Runtime

Sprint 04 introduces AI Runtime as the only interface between AI Workspace and model providers:

```text
AI Workspace
  ↓
AI Runtime
  ↓
Provider Router
  ↓
Prompt Engine
  ↓
Provider Adapter
  ↓
Mock / OpenAI / Ollama / Custom HTTP
```

AI Workspace must not call OpenAI, Ollama, or any other LLM SDK directly.

Primary AI Runtime APIs:

```text
GET  /ai-runtime/providers
POST /ai-runtime/providers
PUT  /ai-runtime/providers/{id}
POST /ai-runtime/providers/{id}/test
GET  /ai-runtime/health
GET  /ai-runtime/logs
POST /ai-runtime/generate
POST /ai-runtime/embed
```

AI Runtime manages:

- Provider routing
- Prompt building
- Prompt version binding
- Mock mode
- Fallback
- Cost and latency logging
- Provider health checks
- Generation logs

Provider types currently supported by the configuration layer:

```text
mock
openai
anthropic
gemini
ollama
custom
custom_http
```

When no real API key is configured, ATOS automatically falls back to `Mock Provider`, so the full AI flow remains runnable offline.

## Semi-Auto Reply Pipeline

Sprint 05 connects the first complete semi-auto reply loop:

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

Default execution mode:

```text
SEMI_AUTO
```

Reserved but not implemented in Sprint 05:

```text
AUTO_ASSISTED
FULL_AUTO
```

Primary Reply Pipeline APIs:

```text
GET  /reply-tasks
POST /reply-tasks
POST /reply-tasks/{id}/approve
POST /reply-tasks/{id}/schedule
POST /reply-tasks/{id}/prepare
POST /reply-tasks/{id}/confirm
```

The Sprint 05 flow never clicks the platform submit/comment button. It only prepares the reply in the browser/editor and enters `WAITING_MANUAL`. The operator must submit manually on the platform, then confirm in ATOS.

Mock mode remains supported without TGE or Playwright. In mock mode, ATOS still creates the Reply Task, Scheduler Task, Execution Task, Browser Session, Browser Tab, platform fill result, timeline metadata, and manual confirmation state transitions.

## Automation Runtime

Sprint 08 adds the long-running automation foundation:

```text
Scheduler
  ↓
Execution Queue
  ↓
Automation Runtime
  ↓
Worker Claim
  ↓
Execution Runtime
  ↓
Result
```

Automation Runtime manages:

- Multiple workers
- Worker heartbeat
- Worker capability scheduling
- Priority queue
- Concurrency control
- Database fallback task locks
- Retry pending flow
- Worker lost recovery
- Runtime metrics
- System alerts

Primary Automation APIs:

```text
GET  /automation/runtime
GET  /automation/workers
POST /automation/workers/register
POST /automation/workers/heartbeat
POST /automation/claim
POST /automation/tasks/{id}/start
POST /automation/tasks/{id}/complete
POST /automation/tasks/{id}/retry
POST /automation/recover
GET  /automation/queue
GET  /automation/locks
GET  /automation/metrics
GET  /automation/alerts
GET  /automation/logs
```

Sprint 08 does not add real browser automation. It makes sure long-running workers can safely claim, retry, and recover execution tasks.

## Intelligence Runtime

Sprint 09 adds the learning layer:

```text
Post / Reply / Execution / Engagement
  ↓
Performance Collection
  ↓
Reply Scoring
  ↓
Aggregation
  ↓
Recommendation
  ↓
Next Strategy
```

Intelligence Runtime tracks:

- Content performance
- Reply scores
- Strategy performance
- Account performance
- Platform performance
- Best time windows
- Prompt performance score
- Duplicate reply similarity
- A/B strategy experiments

Primary Intelligence APIs:

```text
GET  /intelligence/dashboard
GET  /intelligence/recommendations
GET  /intelligence/performance
POST /intelligence/score
POST /intelligence/feedback
POST /intelligence/similarity
GET  /intelligence/similarity
```

Sprint 09 uses local heuristic scoring and mock embeddings. It does not require a vector database or external AI provider.

## Architecture

```text
frontend
  ↓ API
backend
  ↓ ORM / migration
database
  ↓ future queue/cache
redis
```

Primary backend layers:

```text
backend/app/api/             FastAPI routers
backend/app/services/        business and integration services
backend/app/repositories/    database access layer
backend/app/models.py        SQLAlchemy models
backend/alembic/             migrations
```

Primary frontend layers:

```text
frontend/src/App.tsx         layout, routes, screens
frontend/src/api.ts          Axios API client
frontend/src/index.css       theme tokens and shared styles
```

## Folder

```text
ATOS/
├── backend/
├── frontend/
├── docs/
├── scripts/
├── infra/
├── docker/
├── storage/
├── tests/
└── docs/ci/
```

Historical duplicate placeholder directories were removed during Sprint 00.
Production CI checks are stored as `docs/ci/production-check.yml.example`; copy it to `.github/workflows/production-check.yml` only with a GitHub token that has workflow scope.

## Installation

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend
pnpm install
```

If `pnpm` is not installed globally, use Node Corepack or the bundled Codex runtime.

## Environment

Environment templates:

```text
.env.example
.env.local
.env.production
```

Important variables:

```text
DATABASE_URL
APP_ENV
API_BASE_URL
VITE_API_BASE_URL
APIFY_TOKEN
OPENAI_API_KEY
TGE_API_BASE_URL
TGE_API_KEY
PLAYWRIGHT_MOCK_MODE
```

Secrets must not be committed.

## Migration

```bash
.venv/bin/python scripts/migrate.py
```

Equivalent:

```bash
cd backend
../.venv/bin/python -m alembic upgrade head
```

## Seed

```bash
.venv/bin/python scripts/seed.py
```

Seed is idempotent and safe to run repeatedly.

## Development

Start backend:

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start frontend:

```bash
cd frontend
pnpm dev
```

URLs:

```text
Backend:  http://127.0.0.1:8000
Swagger:  http://127.0.0.1:8000/docs
Frontend: http://127.0.0.1:5173
```

## Docker

```bash
docker compose up --build
```

Services:

- `postgres`
- `redis`
- `backend`
- `frontend`
- `pgadmin`

Backend container runs migration and seed before starting the API.

## Production Docker

Production uses PostgreSQL, Redis persistence, backend, frontend, worker, scheduler, and Nginx.

```bash
cp .env.production.example .env.production
docker compose -f docker-compose.prod.yml up -d --build
```

Production health:

```bash
python scripts/smoke_test.py
```

Backup:

```bash
scripts/backup/postgres_backup.sh
scripts/backup/storage_backup.sh
```

## Build

```bash
cd frontend
pnpm build
```

## Run Quality Checks

```bash
make quality
```

Equivalent:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m compileall backend/app backend/scripts scripts
PYTHONPATH=backend .venv/bin/python -m unittest discover backend/tests
cd frontend && pnpm lint
cd frontend && pnpm build
```

## API Response

All APIs must return:

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "trace_id": "...",
  "data": {}
}
```

Errors use the same shape with `success=false`.

## Development Guide

See:

```text
docs/DEVELOPMENT.md
```

## Sprint Report

See:

```text
docs/sprints/Sprint-00.md
docs/sprints/Sprint-01.md
docs/sprints/Sprint-02.md
docs/sprints/Sprint-03.md
docs/sprints/Sprint-10.md
docs/sprints/Sprint-11.md
docs/sprints/Sprint-12.md
docs/sprints/Sprint-13.md
docs/sprints/Sprint-14.md
docs/sprints/Sprint-15.md
docs/SUBMISSION_RUNTIME.md
docs/SUBMISSION_HARDENING.md
docs/AUTO_ASSISTED_MODE.md
docs/REPLY_TEMPLATE_STRATEGY.md
docs/DEPLOYMENT_PRODUCTION.md
docs/PRODUCTION_CHECKLIST.md
docs/KNOWN_LIMITATIONS.md
docs/WORKER_TOKEN_SECURITY.md
docs/manual/ATOS_ADMINISTRATOR_MANUAL.md
docs/releases/RELEASE_NOTES_v1.0_draft.md
docs/platforms/X_ADAPTER.md
```

## Reply Template Strategy

Sprint 14 adds five built-in Chinese reply templates and platform rules:

- `纯帮助，不引流`
- `软引导主页`
- `引导到大号`
- `直接外链`
- `不引导，信任建设`

Use AI Workspace to select a template before generating or approving a reply. Use System Settings -> Reply Templates to manage template risk, platform rules, daily ratios, and AUTO_ASSISTED eligibility.
