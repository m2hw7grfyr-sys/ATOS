# Migration Test

Version: 1.0.0-rc.1

## Empty Database Migration

Command:

```bash
DATABASE_URL=sqlite:////private/tmp/atos_sprint16_empty.db PYTHONPATH=. ../.venv/bin/alembic -c alembic.ini upgrade head
```

Result: Passed.

All migrations from base through `0024` completed.

## Existing Database Upgrade

Command:

```bash
DATABASE_URL=sqlite:////private/tmp/atos_sprint16_existing.db PYTHONPATH=. ../.venv/bin/alembic -c alembic.ini upgrade 0012
DATABASE_URL=sqlite:////private/tmp/atos_sprint16_existing.db PYTHONPATH=. ../.venv/bin/alembic -c alembic.ini upgrade head
```

Result: Passed.

The database upgraded from `0012` to current head.

## Seed Idempotency

Commands:

```bash
DATABASE_URL=sqlite:////private/tmp/atos_sprint16_empty.db PYTHONPATH=backend .venv/bin/python scripts/seed.py
DATABASE_URL=sqlite:////private/tmp/atos_sprint16_empty.db PYTHONPATH=backend .venv/bin/python scripts/seed.py
```

Result: Passed.

The second run reported that the seed marker already exists and did not duplicate core seed data.

## Known Notes

PostgreSQL-specific migration validation must be repeated during Docker production validation.

