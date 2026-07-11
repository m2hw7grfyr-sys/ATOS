# ATOS v1.0 Draft Release Notes

Status: Draft

## Core Features

- Data Center with Apify data source scaffold
- Post Pool
- AI Runtime with Mock / Provider abstraction
- Scheduler Runtime
- Execution Runtime
- Browser Runtime
- Platform Runtime
- Automation Runtime
- Intelligence Runtime
- Submission Runtime
- Reply Template & Funnel Strategy Layer

## Supported Platforms

- Reddit: semi-auto reply flow and adapter scaffold
- X: semi-auto reply flow and adapter scaffold
- Facebook: scaffold
- Instagram: scaffold
- TikTok: scaffold

## Execution Modes

- `SEMI_AUTO`: supported default
- `AUTO_ASSISTED`: policy-gated scaffold and test mode
- `FULL_AUTO`: not open for production use

## Deployment

- Local development with SQLite
- Docker Compose development
- Docker Compose production with PostgreSQL, Redis, Nginx
- Cloudflare Tunnel or Nginx + Certbot HTTPS guide

## Known Limits

- Real full automation is not released.
- External platform selectors require ongoing maintenance.
- Worker runtime is production scaffold and requires real workstation validation.
- Facebook / Instagram / TikTok are placeholders.

## Next Version Plan

- Complete production auth and RBAC enforcement
- Harden real worker registration and rotation UI
- Expand replay evidence UI
- Add S3 / Google Drive backup adapters
- Add richer monitoring integrations
