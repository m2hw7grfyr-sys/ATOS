# Sprint-14: Reply Template & Funnel Strategy Layer

## Sprint Goal

Build the Reply Template and Funnel Strategy layer so every AI reply has a clear template type, funnel intent, CTA strength, platform rule, and performance record.

## Completed Issues

- Added `reply_templates`.
- Added `platform_template_rules`.
- Added `reply_template_performance`.
- Added template fields to `reply_tasks`.
- Added five built-in Chinese templates.
- Added default Reddit, X, Facebook, Instagram, and TikTok platform rules.
- Added `TemplateSelectionEngine`.
- Integrated template selection into AI reply generation and prompt preview.
- Integrated template guard into reply approval.
- Integrated template risk check into Submission / AUTO_ASSISTED policy.
- Added dashboard template metrics.
- Added Intelligence Runtime template performance analysis.
- Added Reply Template management UI in System Settings.
- Added Template Performance UI.
- Added demo seed data.
- Added operator manual section.

## Built-in Templates

1. 纯帮助，不引流
2. 软引导主页
3. 引导到大号
4. 直接外链
5. 不引导，信任建设

## Platform Rules

Reddit:

- Direct link templates are blocked by default.
- Main-account CTA is limited and not AUTO_ASSISTED by default.
- Pure help and trust-building are preferred.

X:

- Main-account CTA is allowed.
- Direct link CTA is allowed only with a limited daily ratio.
- High-risk templates are not AUTO_ASSISTED by default.

Facebook / Instagram / TikTok:

- Conservative rules are created for future expansion.

## AI Runtime Integration

AI reply generation now receives:

- `reply_template_id`
- `reply_template_name_cn`
- `funnel_intent`
- `cta_strength`
- `platform_rule_allowed`

The prompt role instruction is selected from the template. AI is no longer responsible for independently deciding whether to include CTA behavior.

## Known Issues

- Historical success rate is scaffolded but not yet deeply weighted.
- Template ratio control uses current-day Reply Task counts.
- Template performance depends on seed/demo and Submission Runtime events until live traffic is connected.
- Real platform behavior still depends on selector stability from earlier runtimes.

## Next Sprint Recommendation

- Add richer per-community template rules.
- Add template A/B experiments.
- Add account-age-level weighting.
- Add template recommendation explanations in AI Workspace.
- Add chart visualizations for template performance.
