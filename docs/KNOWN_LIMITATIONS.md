# ATOS Known Limitations

## v1.0 Supported Platforms

ATOS v1.0 supports Reddit and X as the release platforms.

Reddit and X support semi-auto reply preparation flows and adapter-backed test mode.

The system can prepare, schedule, and track reply tasks. Real platform behavior depends on login state, selectors, and browser profile health.

## AUTO_ASSISTED Limits

AUTO_ASSISTED is strictly policy-gated.

Production requires:

- global switch
- platform switch
- account switch
- daily limit
- time window
- healthy worker
- audit enabled
- screenshot enabled
- verification enabled

High-risk reply templates are not default AUTO_ASSISTED candidates.

## FULL_AUTO

FULL_AUTO is not open for production operation.

## Reserved Platforms

Facebook, Instagram, and TikTok currently have scaffold adapters only. They are not v1.0 supported production platforms.

## Platform Page Changes

External platform DOM and UI changes may break selectors.

Platform adapters and selector registries must be maintained continuously.

ATOS v1.0 does not guarantee that third-party platform pages remain stable over time.

## Login State

Real production runs require manual validation of:

- account login state
- proxy health
- TGE profile health
- browser session stability

Real platform login state must be maintained by the operator.

## Backup Adapters

Local backup scripts are included. S3 and Google Drive adapters are reserved.

## Authentication

Role definitions exist, but production deployments should enforce access with a secure reverse proxy, Cloudflare Access, VPN, or future internal auth UI before exposing the console.
