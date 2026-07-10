# Sprint 04: AI Runtime

## Sprint Goal

Build AI Runtime as the only interface between AI Workspace and LLM providers.

AI Workspace must not directly call:

- OpenAI
- Ollama
- Anthropic
- Gemini
- Custom HTTP providers
- Any provider-specific SDK

## Milestone

AI Runtime Ready.

## Issue List

- Issue-0401 AI Runtime
- Issue-0402 Provider Adapter
- Issue-0403 Mock Provider
- Issue-0404 OpenAI Provider
- Issue-0405 Ollama Provider
- Issue-0406 Provider Router
- Issue-0407 Prompt Engine
- Issue-0408 Prompt Version
- Issue-0409 AI Request DTO
- Issue-0410 AI Response DTO
- Issue-0411 Task Type
- Issue-0412 Fallback Engine
- Issue-0413 Generation Logs
- Issue-0414 AI Health
- Issue-0415 AI Workspace Integration
- Issue-0416 System Settings
- Issue-0417 API
- Issue-0418 Security
- Issue-0419 Seed
- Issue-0420 README

## Completed

- Added `AIRuntime` as the unified AI provider boundary.
- Added `ProviderAdapter` abstraction with generate text, JSON, embedding, config validation, health check, and cost estimation methods.
- Added runtime wrappers for existing Mock, OpenAI, and configurable provider implementations.
- Added `ProviderRouter` and normalized `REPLY` / `REPLY_GENERATION` routing compatibility.
- Added `PromptEngine` with prompt template lookup, prompt version binding, prompt context, final prompt rendering, and prompt hash tracking.
- Added `AIRequest`, `AIResponse`, and standard task types: `ANALYSIS`, `REPLY_GENERATION`, `REWRITE`, `EMBEDDING`, `CLASSIFICATION`, and `SUMMARY`.
- Refactored AI analysis and reply generation services to call `AIRuntime`.
- Added `/ai-runtime/providers`, `/ai-runtime/health`, `/ai-runtime/logs`, `/ai-runtime/generate`, and `/ai-runtime/embed`.
- Enhanced `ai_generation_logs` with provider id, provider type, model name, task type, prompt template id, final prompt hash, latency, and error code.
- Added seed data for Mock, OpenAI, and Ollama provider configuration.
- Added provider routing seed for `REPLY_GENERATION`.
- Preserved offline Mock Provider behavior when real API keys are absent.

## Acceptance

Implemented:

```text
AI Workspace -> AI Runtime -> Provider Router -> Prompt Engine -> Provider Adapter
```

The default path remains mock-safe and does not require OpenAI, Ollama, or other live provider credentials.

## Security

- Provider API keys are not returned in clear text by runtime provider endpoints.
- Provider API keys are masked in UI-facing responses.
- Empty API key updates keep the existing secret unchanged.
- Generation logs store provider metadata and prompt hashes, not raw provider secrets.

## Known Issues

- Anthropic, Gemini, Ollama, and custom HTTP providers use the configurable provider scaffold until their production adapters are expanded.
- Embedding currently records a mock-safe flow unless a provider returns embedding payloads in the expected format.
- Cost estimation is approximate when providers do not return token usage.
- AI Runtime provider health is synchronous in this sprint.

## Quality Check

Validated:

- Backend compile check
- Backend unit tests
- AI Runtime unit tests
- Alembic migration
- Seed run
- Repeated seed run
- Frontend lint and build

## Commit Hash

See final response or `git log -1 --oneline`.

## Next Sprint

Sprint 05 can start after this sprint is pushed.
