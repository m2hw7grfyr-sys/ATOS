# Core Workflow Test

Version: 1.0.0-rc.1

## Scope

Validate the release-candidate business chain:

Post Pool -> AI Runtime -> Reply Template -> Review -> Scheduler -> Execution -> Browser Runtime -> Platform Runtime -> Submission Runtime -> Manual Confirm / AUTO_ASSISTED.

## Result

Passed in mock/test-mode scope.

## Evidence

- Seed data includes Reddit and X posts, AI tasks, replies, scheduler tasks, execution tasks, browser sessions, platform registry entries, reply tasks, and submission tasks.
- Backend tests passed: 45 tests.
- Smoke test confirmed runtime health endpoints and submission dashboard.
- Release version is visible through `/health` and Dashboard summary.

## Platform Coverage

- Reddit Test Mode: Covered by seeded tasks and adapter scaffolds.
- X Test Mode: Covered by seeded X posts, X adapter data, and submission tasks.

## Limitation

Real browser/platform execution was not performed in this local RC validation. Production validation must rerun this test with real TGE/worker/browser credentials.

