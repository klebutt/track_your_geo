## Context

Plain-language report (`build_plain_report`) already aggregates unique queries into X/N wins and competitor-only losses, but `loss_queries` is a list of query strings. Sales Outreach needs firm names. Dashboard shows the plain report above Summary/Insights; LLM recommendations remain a separate Insights block.

## Goals / Non-Goals

**Goals:**

- Surface tracked competitor names on losses from stored `competitors_mentioned`.
- Shape API fields + UI for a 60-second customer scan (what / result / who / meaning / deeper CTA).
- Deterministic deeper-insights close aligned with soft £5–20 WTP probes.
- Dual-score honesty in Summary without changing the scoring formula.

**Non-Goals:**

- Freeform extraction of untracked firm names from reply text.
- Changing composite score behaviour at 0% visibility.
- Rewriting the LLM recommendations prompt.
- PDF/AI Recommend export branding (Sales/BD pack).
- Probe set / model mix changes.

## Decisions

1. **Loss entries from existing evidence** — Build `loss_entries: [{query, competitors[]}]` by unioning true keys in `competitors_mentioned` across models for brand-miss queries. Cap at `max_list` (5). Derive `loss_queries` from entry queries for back-compat.
2. **Honest empty** — Brand-miss with no tracked competitor hits is not a “loss entry”; gap copy + optional miss note covers it. Do not invent names.
3. **Deterministic deeper insights** — Fixed three forks (who/phrases by model · locality action plan · re-test). No LLM. Shown only on the plain-report panel; Insights keeps LLM recs labeled as operator depth.
4. **Copy fields on `PlainReportOut`** — `what_this_is`, `meaning` (from gap + competitor_summary), `competitor_summary`, `index_note` for Summary one-liner. Geography/models notes retained.
5. **Rebuild on read** — `RunOut` validator already calls `build_plain_report`; completed runs pick up new fields without re-probe.

## Risks / Trade-offs

- [Hamilton shows few named rivals] → Correct; copy states no tracked competitors named — trust over vanity.
- [Operator confusion: SEO recs still in Insights] → Label Insights as operator/depth; plain report is the customer hero.
- [Breaking clients expecting only `loss_queries`] → Keep field populated from `loss_entries`.

## Migration Plan

Deploy API + web together. No DB migration. Rollback = revert change; old UI ignores new fields.

## Open Questions

None for this change.
