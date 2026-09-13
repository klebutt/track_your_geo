## Why

The dashboard still speaks in GEO jargon (visibility %, composite score, probe tables). For the ~50 accountant outreach experiment we need a shareable summary that answers “Does AI recommend you?” in plain language — without asking firms to learn GEO scoring.

## What Changes

- Add a **plain-language report** view (operator-facing first) derived from an existing completed run: headline “AI recommends you in X/N searches”, strongest themes, where competitors win instead, and a short gap summary.
- Prefer **deterministic derivation** from stored `query_results` / visibility / competitor flags — no new LLM call required for the core report (recommendations v1 can still be linked as “what to do next”).
- Keep technical GEO sections available below or behind the plain summary for operators; do not remove scoring.
- Out of scope: paywall, PDF export, public self-serve landing, Railway deploy, changing the 3-model probe set.

## Capabilities

### New Capabilities

- `plain-language-report`: Customer-friendly summary of a GEO run using recommend-rate language, wins/losses, and competitor contrast — minimising GEO jargon.

### Modified Capabilities

- (none required at requirement level for geo-probe/url-intake; report consumes existing run payloads)

## Impact

- Frontend: `apps/web` dashboard (new report section or page for URL/demo runs)
- Optional thin API helper if we want a stable `report` object on `GET /api/runs/{id}` (otherwise compute in UI from existing fields)
- Eval: unit tests for recommend-count / win-loss helpers
- Cost: ~$0 extra if deterministic; outreach still ~$0.50/run for probes
