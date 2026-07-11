# ATOS Known Limitations

## Reddit / X Current Scope

Reddit and X support semi-auto reply preparation flows and adapter scaffolds.

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

Facebook, Instagram, and TikTok currently have scaffold adapters only.

## Platform Page Changes

External platform DOM and UI changes may break selectors.

Platform adapters and selector registries must be maintained continuously.

## Login State

Real production runs require manual validation of:

- account login state
- proxy health
- TGE profile health
- browser session stability

## Backup Adapters

Local backup scripts are included. S3 and Google Drive adapters are reserved.

## Authentication

Role definitions exist, but production deployments should enforce access with a secure reverse proxy, Cloudflare Access, VPN, or future internal auth UI before exposing the console.
