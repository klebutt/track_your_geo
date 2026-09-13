## Why

Sales Outreach critique of Hamilton-Eddy and Hewitt sample reports: the plain report opens with a clear X/N gap, then loses conversion — competitor losses list *queries* instead of firm names, dual scores confuse, and generic SEO actions close the loop instead of teeing soft “deeper insights” WTP. Fix before scaling ~50 outreach reports.

## What Changes

- Plain-language report loss surface shows **named tracked competitors** per lost search (from existing `competitors_mentioned`), plus an honest empty state when none were named.
- Customer-facing report hierarchy: what this is → X/N → who instead → meaning → deeper-insights CTA; demote empty wins and full probe dumps from the hero.
- Deterministic **deeper insights** block (2–3 soft £5–20-aligned forks) on the plain report; LLM recommendations stay in Insights for operators.
- Dual-score framing: lead with X/N; one-liner when visibility/composite appear in Summary — no scoring formula change.
- Keep `loss_queries` derived for back-compat.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `plain-language-report`: named competitor losses, 60s hierarchy fields, deeper-insights close, index honesty framing.

## Impact

- `apps/api/tygeo/plain_report.py`, `schemas.py` (via `PlainReportOut`)
- `apps/web/src/App.tsx` plain-report panel (+ light CSS if needed)
- `eval/test_plain_report.py`
- Vault sample reports refreshed after ship
- No probe set, scoring formula, or model-mix changes; no new LLM call for the core report
