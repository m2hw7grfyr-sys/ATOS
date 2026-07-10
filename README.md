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
└── .github/
```

Historical duplicate placeholder directories were removed during Sprint 00.

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
```
