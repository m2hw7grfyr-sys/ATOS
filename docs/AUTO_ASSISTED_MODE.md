# AUTO_ASSISTED Mode

Version: Sprint 13

Status: Safety-gated scaffold

---

## Definition

`AUTO_ASSISTED` is an execution mode between `SEMI_AUTO` and `FULL_AUTO`.

It is designed for a reviewed reply task that has already passed human review.

In this implementation, `AUTO_ASSISTED` is guarded by policy checks and falls back to manual handling when any guard fails.

Real platform auto-submit remains disabled in this build. Test Mode can simulate submit, verify, result capture, and statistics without clicking a real platform submit button.

---

## Difference From SEMI_AUTO

`SEMI_AUTO`:

- Opens and prepares the reply.
- Enters `WAITING_MANUAL`.
- Requires the operator to submit on the platform.
- Requires the operator to confirm in ATOS.

`AUTO_ASSISTED`:

- Requires an approved reply.
- Runs `ExecutionPolicyEngine`.
- Requires global, platform, and account permissions.
- Runs only in Test Mode for simulated submit in this build.
- Falls back to `WAITING_MANUAL` or `MANUAL_REQUIRED` when blocked.

---

## Difference From FULL_AUTO

`FULL_AUTO` is not open in the current version.

`FULL_AUTO` remains configuration-only and is not exposed as an operational path for normal users.

---

## Policy Engine

Before an `AUTO_ASSISTED` attempt, ATOS checks:

- Reply task is approved.
- `execution_mode = AUTO_ASSISTED`.
- Global AUTO_ASSISTED is enabled.
- AUTO_ASSISTED Test Mode or real-submit mode is enabled.
- Platform AUTO_ASSISTED is enabled.
- Account `allow_auto_assisted = true`.
- Account is active and not high risk.
- Account daily AUTO_ASSISTED limit is not exceeded.
- Platform time window allows execution.
- Platform capability includes `AUTO_SUBMIT`.
- Worker is healthy.
- Browser session is normal.
- Screenshot capture is enabled.

Any failed check blocks the attempt and records audit/log entries.

---

## Reddit Flow

Reddit supports the AUTO_ASSISTED scaffold:

1. Policy check.
2. Mock submit in Test Mode.
3. Verification.
4. Result capture.
5. Daily limit counter update.

Real Reddit submit clicking is disabled in this build.

---

## X Flow

X supports the AUTO_ASSISTED scaffold:

1. Policy check.
2. Mock submit in Test Mode.
3. Verification.
4. Result capture.
5. Daily limit counter update.

Real X submit clicking is disabled in this build.

---

## Manual Fallback

Fallback examples:

- `LOGIN_REQUIRED` -> `MANUAL_REQUIRED`
- `RATE_LIMITED` -> `MANUAL_REQUIRED`
- `REPLY_BOX_NOT_FOUND` -> `FAILED`
- `VERIFICATION_FAILED` -> `MANUAL_REVIEW`
- `WORKER_OFFLINE` -> `RETRY_PENDING`
- `BROWSER_DISCONNECTED` -> `RETRY_PENDING`

---

## Emergency Stop

Emergency Stop:

- Disables global AUTO_ASSISTED.
- Disables platform AUTO_ASSISTED.
- Resets default execution mode to `SEMI_AUTO`.
- Moves pending AUTO_ASSISTED tasks back to `WAITING_MANUAL`.
- Writes audit logs.

---

## Audit

AUTO_ASSISTED records:

- `AUTO_ASSISTED Enabled`
- `AUTO_ASSISTED Disabled`
- `Policy Checked`
- `Policy Passed`
- `Policy Blocked`
- `Auto Submit Started`
- `Auto Submit Completed`
- `Verification Started`
- `Verification Completed`
- `Verification Failed`
- `Manual Fallback`

