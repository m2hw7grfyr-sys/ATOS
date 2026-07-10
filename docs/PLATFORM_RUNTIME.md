# ATOS Platform Runtime

Version: Sprint 07

Status: Implemented Scaffold

---

## Purpose

Platform Runtime is the only platform entry point in ATOS.

Business services must not call Reddit, X, Facebook, Instagram, TikTok, selectors, or browser DOM logic directly.

Execution flow:

```text
Execution
-> Platform Runtime
-> Platform Adapter
-> Browser Runtime / Page
```

---

## Adapter Architecture

All platform adapters implement one interface:

```text
PlatformAdapter
```

Required methods:

- authenticate()
- health_check()
- open_post()
- find_reply_box()
- fill_reply()
- browse()
- like()
- visit_profile()
- get_profile()
- get_post()
- close()

Current adapters:

- RedditAdapter
- XAdapter
- FacebookAdapter
- InstagramAdapter
- TikTokAdapter

Reddit contains the first real reply-box scaffold.

X, Facebook, Instagram, and TikTok are scaffold adapters for discovery, health, and capability checks.

---

## Capability System

Each adapter declares capabilities.

Example:

```text
Reddit:
- REPLY
- BROWSE
- LIKE
- PROFILE_VISIT

TikTok:
- BROWSE
- LIKE
- PROFILE_VISIT
```

Execution payload includes:

- platform
- action_type
- capability_required

Before Execution prepares an action, Platform Runtime checks whether the platform supports the required capability.

If unsupported, the task is rejected before any browser action.

Example:

```text
TikTok + PREPARE_REPLY -> rejected because REPLY is unsupported
```

---

## Platform Registry

The `platform_registry` table stores:

- platform_name
- adapter_name
- enabled
- version
- capabilities
- status
- last_health_check_at
- last_error
- error_count

This makes adapters discoverable and configurable from the UI.

---

## Selector Registry

Selectors are stored in `platform_selectors`.

Sprint 07 extends selector records with:

- platform
- action_type
- selector_key
- selector_value
- version
- enabled

Execution does not own selectors.

Adapters query selectors through Platform Runtime conventions.

---

## API

Platform Runtime endpoints:

- GET `/platform-runtime`
- GET `/platform-runtime/platforms`
- GET `/platform-runtime/health`
- POST `/platform-runtime/capability-check`
- PUT `/platform-runtime/platforms/{registry_id}`
- GET `/platform-runtime/statistics`

All responses use the ATOS standard response envelope.

---

## Adding A New Platform

1. Create a new adapter under `backend/app/adapters/`.
2. Implement `PlatformAdapter`.
3. Declare `platform`, `adapter_name`, `version`, and `capabilities`.
4. Register the adapter in `PlatformRuntime.adapter_classes`.
5. Add selectors through `platform_selectors`.
6. Seed or configure `platform_registry`.
7. Verify with `/platform-runtime/capability-check`.

No business service should need platform-specific changes.

---

## Current Limits

Sprint 07 focuses on architecture and routing.

Real DOM execution remains dependent on Browser Runtime and future platform selector refinement.

TikTok, X, Facebook, and Instagram adapters are intentionally scaffold-only.
