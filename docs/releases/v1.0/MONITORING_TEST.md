# Monitoring Test

Version: 1.0.0-rc.1

## Health Endpoints

Passed:

- `/health`
- `/ready`
- `/live`
- `/metrics`
- `/health/database`
- `/health/redis`
- `/health/worker`
- `/health/scheduler`
- `/health/ai-runtime`
- `/health/browser-runtime`

## Alert Rules

Reviewed:

- Worker offline
- Queue too long
- AI provider error
- Submission failure
- Disk usage

Alert rules are defined in `infra/monitoring/alert_rules.json`.

## Dashboard

Dashboard exposes runtime health, version, environment, and emergency stop status.

## Limitation

External alert delivery integrations are not part of v1.0.

