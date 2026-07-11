# X Adapter

Version: Sprint 11

Status: v1 Semi-auto

## Architecture

X is connected through Platform Runtime.

Business flow:

Post Pool -> AI Workspace -> Scheduler Runtime -> Execution Runtime -> Browser Runtime -> Platform Runtime -> XAdapter -> WAITING_MANUAL -> Submission Runtime

Execution does not call X directly.

## Supported URL

Input URLs:

- `https://x.com/{username}/status/{tweet_id}`
- `https://twitter.com/{username}/status/{tweet_id}`

Canonical URL:

- `https://x.com/{username}/status/{tweet_id}`

Normalized fields:

- `platform = x`
- `external_post_id = tweet_id`
- `source_post_id = tweet_id`
- `author_handle = username`
- `canonical_url`

## Capability

X declares:

- `BROWSE`
- `OPEN_POST`
- `REPLY`
- `REPLY_FILL`
- `MANUAL_CONFIRM`
- `SUBMISSION_SCAFFOLD`
- `LIKE`
- `PROFILE_VISIT`

`AUTO_SUBMIT` is not declared and is not enabled by default.

## Selector Strategy

Selectors live in Platform Selector Registry.

Seed selectors include:

- `reply_button`
- `reply_box`
- `reply_textarea_or_editor`
- `submit_button_scaffold`
- `login_required_indicator`
- `rate_limit_indicator`
- `error_indicator`

Selectors are configurable and versioned.

## SEMI_AUTO Flow

1. Browser Runtime opens the X post.
2. XAdapter normalizes URL.
3. XAdapter checks login and rate limit indicators.
4. XAdapter clicks Reply.
5. XAdapter finds the rich text editor.
6. XAdapter fills the reply content.
7. Execution enters `WAITING_MANUAL`.
8. Operator manually submits on X.
9. Operator confirms in ATOS.
10. Submission Runtime records the result.

## Error Handling

Supported error codes:

- `X_LOGIN_REQUIRED`
- `X_REPLY_BOX_NOT_FOUND`
- `X_EDITOR_NOT_READY`
- `X_RATE_LIMITED`
- `X_PAGE_LOAD_FAILED`
- `X_CONTENT_REJECTED`
- `X_UNKNOWN_ERROR`

Login and rate limit cases must stop fill and require manual handling.

## Manual Confirm

Manual confirmation uses existing APIs:

- `POST /reply-tasks/{id}/confirm`
- `POST /execution/tasks/{id}/mark-submitted`
- `POST /submission/tasks/{id}/record-manual-result`

Submission Runtime stores:

- platform
- reply task
- execution task
- result URL
- external reply ID
- screenshots or replay paths where available

## Known Limitations

- Real X selectors may require adjustment per UI version.
- X auto submit is not implemented.
- X verification is mock-safe and manual-confirm compatible.
- Real screenshot capture depends on the Browser Runtime execution mode.
