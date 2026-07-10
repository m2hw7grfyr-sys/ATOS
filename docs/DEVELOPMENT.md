# ATOS Development Guide

## Local Start

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend
pnpm install
```

## Migration

```bash
.venv/bin/python scripts/migrate.py
```

Migration source:

```text
backend/alembic/
```

Rules:

- Every schema change must add an Alembic migration.
- Empty database migration must pass.
- Re-running `alembic upgrade head` must be safe.

## Seed

```bash
.venv/bin/python scripts/seed.py
```

Seed rules:

- Seed must be idempotent.
- Demo data must not require external services.
- New demo entities must use stable lookup keys.

## Backend Development

API modules live in:

```text
backend/app/api/
```

Service modules live in:

```text
backend/app/services/
```

Repository modules live in:

```text
backend/app/repositories/
```

Rules:

- API handlers should call Service or Repository layers.
- API handlers must return the unified response shape through `ok()`.
- Runtime configuration must go through `ConfigurationService`.
- Business logic must not read `.env` directly.

## Add API

1. Add schema in `backend/app/schemas.py`.
2. Add repository if database access is needed.
3. Add service logic in `backend/app/services/`.
4. Add router in `backend/app/api/`.
5. Register router in `backend/app/main.py`.
6. Add or update tests.

## Add Entity

1. Add SQLAlchemy model in `backend/app/models.py`.
2. Add Alembic migration.
3. Add seed data if needed.
4. Add serializer or API response mapping.
5. Add tests.

## Frontend Development

Frontend entry:

```text
frontend/src/App.tsx
```

API client:

```text
frontend/src/api.ts
```

Rules:

- Pages must use the shared API client.
- Pages must not call `fetch` directly.
- Pages must use the common Layout.
- New screens must be registered in the navigation and route map.
- Permission checks should go through `PermissionGuard`.

## Add Screen

1. Add `PageKey`.
2. Add route in `pageRoutes`.
3. Add navigation item.
4. Add page component.
5. Add page to `PageContent`.

## Quality Check

```bash
make quality
```

Equivalent commands:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m compileall backend/app backend/scripts scripts
PYTHONPATH=backend .venv/bin/python -m unittest discover backend/tests
cd frontend && pnpm lint
cd frontend && pnpm build
```
