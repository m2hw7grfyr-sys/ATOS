# ATOS v1.2 Acceptance Report

Version: v1.2

Status: Accepted with one environment-limited frontend build check

---

## Scope

v1.2 enhances AI Workspace, System Settings, and Statistics.

This release does not add TGE automation, Playwright execution, automatic comment submission, automatic posting, or messaging.

---

## Completed

- Added unified LLM Provider adapter methods:
  - `generate_analysis()`
  - `generate_reply()`
  - `generate_embedding()`
  - `validate_config()`
  - `estimate_cost()`
  - `health_check()`
- Added supported provider types:
  - `mock`
  - `openai`
  - `anthropic`
  - `gemini`
  - `ollama`
  - `custom_http`
  - `custom`
- Added Provider Routing table and API.
- Added Prompt Version table and API.
- Added Prompt Preview API and UI.
- Added Provider health check API and UI action.
- Added fallback chain logging:
  - Primary Provider
  - Fallback Provider
  - Mock Provider
  - Template fallback placeholder
- Added token, latency, and estimated cost fields in AI generation logs.
- Added Dashboard AI metrics:
  - LLM Provider Health
  - Fallback Rate
  - Average Latency
  - AI Cost Today
- Updated seed data with:
  - 2 Prompt Versions
  - 3 Provider Routing rules
- Updated README, CHANGELOG, and TODO.

---

## API Added Or Updated

- `GET /settings/llm-providers`
- `POST /settings/llm-providers`
- `PUT /settings/llm-providers/{id}`
- `POST /settings/llm-providers/{id}/test`
- `GET /settings/provider-routing`
- `POST /settings/provider-routing`
- `PUT /settings/provider-routing/{id}`
- `GET /prompt-templates`
- `POST /prompt-templates`
- `GET /prompt-versions`
- `POST /prompt-versions`
- `POST /ai/tasks/{id}/preview-prompt`

---

## Mock Provider Test

Result: Passed.

Mock Provider remains available without API keys.

Validated by backend unit tests:

- AI analysis runs through Mock Provider.
- Reply generation runs through Mock Provider.
- Generation logs include token totals.

---

## OpenAI Provider Test

Result: Configuration-level test implemented.

Behavior:

- If `api_key` is missing, health check returns `WARNING`.
- If `api_key` and `model_name` are configured, health check returns `HEALTHY`.
- Real network call is not required for the health check.
- Real generation path remains available through the OpenAI chat completions adapter.

---

## Provider Routing Test

Result: Passed.

Validated behavior:

- Routing can select provider by `task_type`.
- Routing can use fallback provider.
- Invalid primary provider is recorded as failed, then fallback is used.

---

## Fallback Test

Result: Passed.

Validated by unit test:

- Broken OpenAI provider without API key falls back to Mock Provider.
- `fallback_used` is recorded.
- `fallback_reason` includes the provider failure reason.
- `fallback_from_provider` and `fallback_to_provider` are recorded.

---

## Prompt Version Test

Result: Passed.

Validated behavior:

- Prompt Versions can be created.
- Default Prompt Version is selected by prompt template.
- AI calls write `prompt_version_id` when a version is available.

---

## Prompt Preview Test

Result: Passed.

Validated behavior:

- AI Workspace can call `POST /ai/tasks/{id}/preview-prompt`.
- Response includes:
  - System Prompt
  - Platform Prompt
  - Strategy Prompt
  - Variables
  - Final Prompt
  - Prompt Version

---

## Token And Cost Statistics

Result: Passed.

Validated behavior:

- AI logs record:
  - `input_tokens`
  - `output_tokens`
  - `total_tokens`
  - `estimated_cost`
  - `provider_latency_ms`
- Dashboard exposes fallback rate, average latency, and estimated AI cost.

---

## Validation Commands

Passed:

```bash
PYTHONPYCACHEPREFIX=.pycache PYTHONPATH=backend python3 -m compileall backend/app backend/scripts
PYTHONPYCACHEPREFIX=.pycache PYTHONPATH=backend .venv/bin/python -m unittest discover backend/tests
DATABASE_URL=sqlite:////private/tmp/atos_v12_migration.db PYTHONPATH=. ../.venv/bin/python -m alembic upgrade head
DATABASE_URL=sqlite:////private/tmp/atos_v12_seed.db PYTHONPATH=backend .venv/bin/python -m backend.scripts.seed_data
```

Frontend build:

```bash
PATH=/Users/zhangkaikai/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH CI=true pnpm build
```

Result: Passed.

Output summary:

```text
tsc -b && vite build
1578 modules transformed
dist/index.html
dist/assets/index-DtwOAirD.css
dist/assets/index-Coil-RWP.js
built in 1.48s
```

---

## Known Issues

- Anthropic, Gemini, Ollama, and custom HTTP providers currently have adapter scaffolds and config validation, but generation is not implemented.
- Provider pricing is a conservative generic estimate, not model-specific.
- Prompt Version editing is create/list only in this release.
- `pnpm approve-builds esbuild` requires Node to be available on PATH when using the bundled runtime.
- Secret Vault is not implemented; API keys are still stored in the local database but are masked in API responses.

---

## Next Step Suggestions

- Add provider-specific pricing configuration.
- Implement real Anthropic, Gemini, Ollama, and custom HTTP generation adapters.
- Add Prompt Diff and Prompt Approval History.
- Add embedding similarity and duplicate reply detection.
- Add AI cost budget alerts.
- Move API keys into a Secret Vault before production use.
