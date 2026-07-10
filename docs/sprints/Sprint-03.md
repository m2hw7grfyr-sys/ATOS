# Sprint 03: Browser Runtime

## Sprint Goal

Build Browser Runtime as the only interface between Execution and browser implementations.

Execution must not directly call:

- Playwright
- TGE
- AdsPower
- Chrome
- Any browser-specific SDK

## Milestone

Browser Runtime Ready.

## Issue List

- Issue-0301 Browser Runtime
- Issue-0302 Browser Adapter
- Issue-0303 TGE Adapter
- Issue-0304 Playwright Adapter
- Issue-0305 Browser Session
- Issue-0306 Browser Tab
- Issue-0307 Browser Manager
- Issue-0308 Browser Health
- Issue-0309 Execution Integration
- Issue-0310 Open URL
- Issue-0311 Close Tab
- Issue-0312 Session Recovery
- Issue-0313 Replay Index
- Issue-0314 Browser Dashboard
- Issue-0315 API
- Issue-0316 Seed
- Issue-0317 README
- Issue-0318 Sprint Report

## Completed

- Added `BrowserRuntime` with start, attach, open URL, close tab, heartbeat, disconnect, and recover.
- Added `BrowserAdapter` abstraction with uniform adapter methods.
- Added `MockBrowserAdapter`, `TGEBrowserAdapter`, and `PlaywrightBrowserAdapter`.
- Added `BrowserManager` for session pool lookup and dead-session detection.
- Added `browser_sessions` and `browser_tabs`.
- Added `/browser/runtime`, `/browser/sessions`, `/browser/tabs`, `/browser/open`, `/browser/close`, and `/browser/recover`.
- Updated Execution API browser-related actions to delegate to Browser Runtime.
- Added Replay Index metadata for session, tab, screenshot, HTML, console, and network placeholders.
- Dashboard now shows Running Browser, Running Tabs, and Dead Sessions.
- Seed now creates 2 workers, 4 browser sessions, and 15 browser tabs.

## Acceptance

Implemented:

```text
Execution -> Browser Runtime -> Browser Adapter -> Playwright Adapter / TGE Adapter
```

The default path remains mock-safe and does not require a real browser.

## Known Issues

- TGE Adapter uses the existing scaffold unless real TGE API settings are enabled.
- Playwright Adapter is available behind the Browser Runtime boundary, but real attach depends on valid websocket/debug info.
- Replay Index stores metadata only in this sprint; it does not require real screenshots, HTML snapshots, console logs, or network logs.
- Older lower-level Playwright runner tests remain to protect previous behavior, but Execution API now delegates browser actions through Browser Runtime.

## Quality Check

Passed:

```bash
make quality
```

Validated:

- Backend compile check
- Backend unit tests
- Frontend TypeScript lint
- Frontend production build
- Alembic migration
- Seed run
- Repeated seed run

## Commit Hash

See final response or `git log -1 --oneline`.

## Next Sprint

Sprint 04 can start after this sprint is pushed.
