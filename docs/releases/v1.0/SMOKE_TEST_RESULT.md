# Smoke Test Result

Version: 1.0.0-rc.1

## Command

```bash
DATABASE_URL=sqlite:////private/tmp/atos_sprint16_empty.db PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8777
.venv/bin/python scripts/smoke_test.py --api-base-url http://127.0.0.1:8777 --skip-frontend --skip-worker
```

## Result

Passed.

## Checked Endpoints

- `/health`
- `/health/database`
- `/health/redis`
- `/health/worker`
- `/health/scheduler`
- `/health/ai-runtime`
- `/health/browser-runtime`
- `/submission/dashboard`
- `/ready`
- `/live`
- `/metrics`

## Version Check

- `/health` returned `version = 1.0.0-rc.1`.
- `/dashboard/summary` returned overview version `1.0.0-rc.1`.

## Skipped

- Frontend reachable check was skipped because this smoke run targeted backend API validation only.
- Worker reachable check was skipped because no remote worker process was started in this local RC run.

