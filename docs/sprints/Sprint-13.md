# Sprint-13

Milestone: AUTO_ASSISTED Stabilization for Reddit + X

## Sprint Goal

Stabilize the `AUTO_ASSISTED` submission mode across Reddit and X with global, platform, and account-level guards.

`SEMI_AUTO` remains the default mode.

`FULL_AUTO` remains unavailable for normal operation.

## Completed Issues

- Added global AUTO_ASSISTED settings.
- Added platform-level AUTO_ASSISTED configuration.
- Added account-level `allow_auto_assisted`.
- Added account daily AUTO_ASSISTED limit structure.
- Upgraded `ExecutionPolicyEngine` with global, platform, account, worker, browser, time-window, capability, screenshot, and approval checks.
- Added AUTO_ASSISTED task states: `SUBMITTING`, `COMPLETED`, `MANUAL_REVIEW`, `RETRY_PENDING`, `VERIFICATION_FAILED`.
- Added `Run AUTO_ASSISTED Now` API and UI action.
- Added Emergency Stop API and UI action.
- Added AUTO_ASSISTED dashboard and submission statistics.
- Added audit logging for policy, submit, verification, fallback, and emergency stop actions.
- Added Test Mode support for safe submit/verify/result simulation.

## Reddit AUTO_ASSISTED Status

Reddit has:

- AUTO_SUBMIT capability scaffold.
- Policy-gated submit path.
- Test Mode submit success.
- Verification and result capture.

Real Reddit submit clicking is disabled in this build.

## X AUTO_ASSISTED Status

X has:

- AUTO_SUBMIT capability scaffold.
- Policy-gated submit path.
- Test Mode submit success.
- Verification and result capture.

Real X submit clicking is disabled in this build.

## Policy Engine Rules

AUTO_ASSISTED requires:

- Approved reply task.
- `execution_mode = AUTO_ASSISTED`.
- Global AUTO_ASSISTED enabled.
- Test Mode enabled or real-submit mode enabled.
- Platform AUTO_ASSISTED enabled.
- Account AUTO_ASSISTED enabled.
- Daily auto-submit limit available.
- Time window available.
- Platform supports `AUTO_SUBMIT`.
- Worker is healthy.
- Browser session is normal.
- Screenshot capture is enabled.

Any failed rule falls back to `WAITING_MANUAL`, `MANUAL_REQUIRED`, `MANUAL_REVIEW`, `RETRY_PENDING`, or `FAILED`.

## Test Results

Expected validation:

- Backend unit tests pass.
- Migration from empty database succeeds.
- Seed from empty database succeeds.
- Frontend build succeeds.
- AUTO_ASSISTED Test Mode can simulate submit, verify, record result.

## Known Issues

- Real platform submit clicking is intentionally disabled.
- Administrator-only RBAC is represented by UI/API structure, not full user auth enforcement.
- Verification is mock-based in Test Mode.

## Next Sprint Recommendation

- Add stronger RBAC enforcement.
- Add richer verification evidence display.
- Add per-platform selector validation screens.
- Keep real submit disabled until compliance and operator risk policy are finalized.

