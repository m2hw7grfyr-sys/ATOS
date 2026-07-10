# Sprint-07: Platform Runtime

Milestone: Platform Runtime

Status: Completed

---

## Sprint Goal

Build a unified Platform Runtime so ATOS business flow can call platforms through adapters instead of hard-coded platform logic.

Target flow:

```text
Post
-> AI
-> Scheduler
-> Execution
-> Platform Runtime
-> Adapter
```

---

## Completed

- Added `PlatformRuntime`.
- Added `PlatformAdapter` interface.
- Added `RedditAdapter`.
- Added scaffold adapters:
  - XAdapter
  - FacebookAdapter
  - InstagramAdapter
  - TikTokAdapter
- Added `platform_registry`.
- Added capability check for execution actions.
- Extended `platform_selectors` with `action_type` and `version`.
- Added Platform Runtime API.
- Added Platform Center page.
- Updated Dashboard with platform overview.
- Added platform statistics scaffold.
- Added seed data for platform registry, selectors, and platform statistics.
- Added backend tests for discovery, capability check, and health registry update.

---

## Capability Model

Current capabilities:

- REPLY
- BROWSE
- LIKE
- PROFILE_VISIT

Reddit supports semi-auto reply preparation.

Other platform adapters are scaffold-first and currently do not support `REPLY`.

---

## API

Added:

- GET `/platform-runtime`
- GET `/platform-runtime/platforms`
- GET `/platform-runtime/health`
- POST `/platform-runtime/capability-check`
- PUT `/platform-runtime/platforms/{registry_id}`
- GET `/platform-runtime/statistics`

---

## UI

Added:

- Platform Center
- Adapter Discovery
- Platform Registry
- Capability Check
- Platform Health
- Platform Statistics

---

## Tests

Covered:

- Adapter discovery
- Reddit reply capability support
- TikTok reply capability rejection
- Platform health writing `platform_registry`

Executed:

- `PYTHONPATH=backend .venv/bin/python -m unittest discover backend/tests`
- `DATABASE_URL=sqlite:////private/tmp/atos_sprint07_migration.db PYTHONPATH=. ../.venv/bin/alembic -c alembic.ini upgrade head`
- `DATABASE_URL=sqlite:////private/tmp/atos_sprint07_migration.db PYTHONPATH=backend .venv/bin/python backend/scripts/seed_data.py`
- `PATH=/Users/zhangkaikai/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH /Users/zhangkaikai/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/pnpm run build`

---

## Known Issues

- X, Facebook, Instagram, and TikTok adapters are scaffolds.
- Real selector stability still depends on future platform-specific verification.
- Platform health is adapter-level only; it does not yet perform real platform login checks.

---

## Commit Hash

See final Git commit hash reported after commit.

---

## Next Sprint

Recommended next sprint:

- Platform selector refinement
- Real platform health checks
- Browser Runtime plus Platform Runtime integration validation
- More platform-specific adapter implementations
