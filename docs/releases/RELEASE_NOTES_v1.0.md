# ATOS v1.0 Release Notes

Version: 1.0.0-rc.1

Status: Release Candidate

## Overview

ATOS v1.0 is the first runnable release candidate of the AI Traffic Operating System. It provides a complete local-to-production foundation for data intake, AI-assisted reply preparation, scheduling, execution orchestration, browser/platform abstraction, submission review, monitoring, and operator documentation.

## Supported Platforms

- Reddit: supported for v1.0 semi-auto/test-mode workflows.
- X: supported for v1.0 semi-auto/test-mode workflows.
- Facebook, Instagram, TikTok: adapter scaffolds only; not v1.0 production-supported platforms.

## Execution Modes

- `SEMI_AUTO`: default supported mode.
- `AUTO_ASSISTED`: available only when enabled by an administrator and allowed by policy checks.
- `FULL_AUTO`: not open in v1.0.

## Core Features

- Dashboard
- Data Center and Post Pool
- AI Runtime and Reply Templates
- Scheduler Runtime
- Execution Runtime
- Browser Runtime
- Platform Runtime
- Automation Runtime
- Submission Runtime
- Statistics and Intelligence foundations
- Emergency Stop controls
- Production health, readiness, liveness, and metrics endpoints

## Deployment

v1.0 includes production scaffolding for:

- Docker Compose production stack
- PostgreSQL
- Redis
- Nginx
- Worker and scheduler service roles
- Backup / restore scripts
- Smoke test script
- Production checklist

## Known Limitations

- Production Docker validation must be rerun on a host with Docker installed.
- Real platform login state must be maintained manually.
- Platform selectors can break when Reddit or X changes page structure.
- Internal production auth UI is not complete; use Cloudflare Access, VPN, or a secure reverse proxy before exposing ATOS.
- AUTO_ASSISTED must remain policy-gated.

## Upgrade Notes

- Update `.env` from `.env.production.example`.
- Confirm `APP_VERSION=1.0.0-rc.1`.
- Run Alembic migrations before starting workers.
- Run seed only for demo/staging environments.
- Run `scripts/smoke_test.py` after deployment.

## Roadmap

Post-v1.0 work is tracked in `docs/ROADMAP_v1.1.md`.

