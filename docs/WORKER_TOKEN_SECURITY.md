# Worker Token Security

Status: Sprint 15

## Purpose

Worker registration and heartbeat must use token authentication.

Tokens must not be hardcoded, printed, committed, or shared in chat logs.

## Configuration

Use:

```text
WORKER_API_TOKEN
WORKER_TOKEN_VERSION
```

Production requires `WORKER_API_TOKEN`.

## Rotation

Recommended rotation:

1. Generate a new long random token.
2. Update server `.env.production`.
3. Update Windows Worker service environment.
4. Restart server and worker.
5. Confirm `/health/worker`.
6. Increment `WORKER_TOKEN_VERSION`.

## Disable

If a token is leaked:

1. Stop worker registration.
2. Rotate token immediately.
3. Restart workers.
4. Review `audit_logs` and worker logs.

## Logging

Do not log:

- raw token
- Authorization header
- API key

Dashboard and logs may show token version only.
