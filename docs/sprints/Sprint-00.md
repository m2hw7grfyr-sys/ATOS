# Sprint 00: Project Foundation

## Sprint Goal

Establish the long-term development foundation for ATOS without adding business features.

## Issue List

- Issue-0001 Project Structure
- Issue-0002 Environment
- Issue-0003 Docker
- Issue-0004 Database
- Issue-0005 Seed
- Issue-0006 Configuration Service
- Issue-0007 Logging
- Issue-0008 API Response
- Issue-0009 Exception Handler
- Issue-0010 Frontend Layout
- Issue-0011 Theme
- Issue-0012 Routing
- Issue-0013 State
- Issue-0014 HTTP Client
- Issue-0015 Repository
- Issue-0016 Git
- Issue-0017 README
- Issue-0018 Developer Documentation
- Issue-0019 Acceptance
- Issue-0020 Quality Check

## Completed

- Repository structure normalized to root-level `backend/`, `frontend/`, `docs/`, `scripts/`, `infra/`, `docker/`, `storage/`, `tests/`, `.github/`.
- Historical duplicate placeholder directories removed.
- Unified environment templates added: `.env.example`, `.env.local`, `.env.production`.
- Docker Compose scaffold added for PostgreSQL, Redis, backend, frontend, and pgAdmin.
- Root seed entrypoint added: `python scripts/seed.py`.
- Root migration entrypoint added: `python scripts/migrate.py`.
- Configuration Service added.
- JSON request logging added.
- API response order normalized.
- Global exception handling extended for database errors.
- Axios API client added.
- React Router integrated with the existing shared App Layout.
- Repository base class added for future backend modules.
- README and development guide updated.
- Git ignore rules expanded for caches, logs, local DBs, build output, and dependencies.

## Known Issues

- Full Repository Pattern migration is foundational only; many existing API handlers still directly use SQLAlchemy and should be moved module by module in future sprints.
- Permission Guard is a placeholder and does not enforce RBAC yet.
- Docker Compose scaffold is present, but this machine does not have the `docker` command installed, so `docker compose up` could not be executed locally.
- Production hardening is not included.

## Quality Check

Passed:

```bash
make quality
```

Validated:

- Backend compile check
- Backend unit tests: 13 tests
- Frontend TypeScript lint
- Frontend production build
- Empty database Alembic migration
- Seed run
- Repeated seed run

## Commit Hash

See final response or `git log -1 --oneline`.

## Next Sprint

Sprint 01 can start after quality checks pass and this Sprint is pushed.
