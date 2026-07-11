# Reply Template Strategy

Status: Sprint 14

## Purpose

Reply Template Strategy gives every AI reply an explicit funnel intent and CTA strength.

AI is not allowed to randomly decide whether to lead users to a profile, main account, or link. The selected template, platform rule, and approval guard must decide that first.

## Built-in Templates

| 中文名称 | Funnel Intent | CTA Strength | Risk |
| --- | --- | --- | --- |
| 纯帮助，不引流 | NO_CTA | NONE | LOW |
| 软引导主页 | PROFILE_CTA | SOFT | LOW_MEDIUM |
| 引导到大号 | MAIN_ACCOUNT_CTA | MEDIUM | MEDIUM |
| 直接外链 | DIRECT_LINK_CTA | STRONG | HIGH |
| 不引导，信任建设 | TRUST_BUILDING | NONE | LOW |

## Funnel Intent

- `NO_CTA`: no lead action.
- `PROFILE_CTA`: soft profile or pinned-content hint.
- `MAIN_ACCOUNT_CTA`: natural mention of a main account or thread.
- `DIRECT_LINK_CTA`: direct outbound link intent.
- `TRUST_BUILDING`: relationship and credibility only.

Future intents may include `THREAD_CTA`, `BIO_CTA`, and `DM_CTA`.

## CTA Strength

- `NONE`: no CTA.
- `SOFT`: light hint only.
- `MEDIUM`: clear but natural redirection.
- `STRONG`: direct link or direct conversion action.

## Platform Rules

Platform rules are stored in `platform_template_rules`.

Default policy:

- Reddit allows pure help, soft profile CTA, limited main-account CTA, and trust-building.
- Reddit blocks direct links by default.
- X allows pure help, soft profile CTA, main-account CTA, and limited direct links.
- Facebook, Instagram, and TikTok start with conservative defaults.

Administrators can change rules in System Settings -> Reply Templates.

## Template Selection Engine

`TemplateSelectionEngine` selects a template using:

- platform
- post score
- risk score
- account health
- community rule level
- historical success rate
- operator preference

If the selected template is blocked by platform rule or daily ratio, the engine downgrades to a safer template.

## Ratio Control

Daily ratio control prevents overusing high-risk or aggressive templates.

Examples:

- Reddit direct links default to `0`.
- Reddit soft profile CTA defaults to `0.3`.
- X direct link CTA defaults to `0.15`.

## Approval Guard

Reply approval checks:

- selected template exists
- template is enabled
- platform rule allows the template
- daily ratio is still available

If a rule blocks the template, approval fails and an audit log is written.

## AUTO_ASSISTED Guard

Execution policy checks template risk before AUTO_ASSISTED.

High-risk templates and rules are not eligible for AUTO_ASSISTED by default. They must stay in semi-auto or manual review.

## Performance Tracking

`reply_template_performance` tracks:

- generated
- approved
- submitted
- verified
- failed
- engagement
- conversion
- success rate
- failure rate

Dashboard and Intelligence Runtime read this table to show template performance and recommendations.

## Best Practices

- Use `纯帮助，不引流` and `不引导，信任建设` for early account trust.
- Use `软引导主页` sparingly on Reddit.
- Use `引导到大号` mainly on X or platforms where account-to-account discovery is natural.
- Keep `直接外链` disabled on Reddit unless an administrator intentionally changes the rule.
- Treat high-risk templates as manual review items.
