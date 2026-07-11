# SEMI_AUTO Regression Test

Version: 1.0.0-rc.1

## Expected Flow

1. AI generates reply.
2. Operator reviews reply.
3. Scheduler queues task.
4. Worker executes task.
5. Browser Runtime opens page.
6. Platform Runtime fills reply.
7. Task enters `WAITING_MANUAL`.
8. Operator confirms.
9. Result is recorded.

## Result

Passed in mock/test-mode scope.

## Coverage

- Reddit: seeded semi-auto reply flow present.
- X: seeded semi-auto reply flow present.
- `WAITING_MANUAL`: present in submission dashboard and execution task states.
- Manual confirmation path: API and UI structure present from previous sprint hardening.

## Limitation

No real platform page was opened in this local RC run.

