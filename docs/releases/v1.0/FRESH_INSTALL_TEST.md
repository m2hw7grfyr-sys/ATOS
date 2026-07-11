# Fresh Install Test

Version: 1.0.0-rc.1

## Scope

Simulate a new operator installing ATOS from a clean checkout.

## Expected Procedure

```bash
git clone https://github.com/m2hw7grfyr-sys/ATOS.git
cd ATOS
cp .env.production.example .env
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend alembic -c backend/alembic.ini upgrade head
docker compose -f docker-compose.prod.yml exec backend python scripts/seed.py
python scripts/smoke_test.py --api-base-url https://atos.example.com
```

## Local RC Result

Status: Blocked by local environment.

The current validation host does not have the `docker` command installed, so Docker Compose startup could not be executed locally.

## What Was Verified Instead

- Backend Python build passed.
- Frontend production build passed.
- Empty SQLite migration passed.
- Seed execution passed.
- Seed idempotency passed.
- Local smoke test passed against a migrated and seeded database.

## Release Impact

Release candidate tag is withheld until Docker fresh install is validated on a Docker-enabled machine.

