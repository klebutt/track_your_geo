# Proposal: per-query citation domains

## Why

Commercial stakeholders need **Journey 2** visibility into which sources appear in generative answers. The MVP already stores full model replies but does not surface domains cited in that text. Showing **per-query domains** (with a simple brand-owned vs third-party split) makes diagnosis credible without changing the probe model or score.

## What Changes

- Deterministic **domain extraction** from each stored `response_text` (HTTP(S) URLs and markdown links).
- Persist **`cited_domains`** on each `query_results` row: `{ domain, kind }` where `kind` is `brand_owned` or `third_party`.
- Optional pilot config **`brand_domains`** for explicit ownership; heuristic fallback from brand name slug when unset.
- API exposes `cited_domains` on run query results.
- Dashboard: per-query domain chips in the results table and under each full reply; empty state when none found.
- Remove the standalone **illustrative `seed_domains`** panel from the UI (config field may remain for compatibility).
- **No change** to probe prompts, model (`gpt-4o-mini`), LiteLLM path, or `composite_score`.

## Capabilities

### New Capabilities

<!-- None — extends existing geo-probe capability -->

### Modified Capabilities

- `geo-probe`: Add citation domain extraction, persistence, API exposure, and UI display requirements; clarify empty-state behaviour.

## Impact

- `apps/api/tygeo/` — new `citations.py`, `analysis.py`, `models.py`, `schemas.py`, `pilots.py`, `hardcoded_pilots.py`, `db.py` (SQLite column migration)
- `apps/web/src/App.tsx`, `App.css`
- `eval/` — unit tests for extraction and classification
- `openspec/specs/geo-probe/spec.md` updated when change is archived
