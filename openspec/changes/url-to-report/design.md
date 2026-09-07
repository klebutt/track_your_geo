## Context

Track Your GEO already runs multi-model probes from YAML `PilotProfile`s, scores visibility (substring + extraction), and emits recommendations. Operators need to analyse ~50 accountants with **only a website URL** — no multi-field forms. Vault strategy (`next-development-phases.md`) locks the experiment vertical to accountants and treats 1–2 hand-written profiles as gold calibration only.

## Goals / Non-Goals

**Goals:**

- URL-only intake that infers a business profile + query set and kicks off the existing analysis pipeline
- Schema support for `url`, `aliases`, and related fields; alias-aware visibility matching
- Accountant query templates + light LLM fill from inferred location/services
- Operator-usable API + minimal UI in the current prototype
- Logged cost for inference steps; deterministic tests with mocks

**Non-Goals:**

- Stripe / paywall / public marketing landing polish
- Accountant-facing confirm-profile forms
- Auth / multi-tenancy
- Cron, email, batch job queue product
- Perfect NER / knowledge-graph entity linking
- Multi-vertical template packs beyond accountants in this change

## Decisions

### 1. Extend `PilotProfile` rather than a parallel Business model (for this change)

**Choice:** Add optional fields to `PilotProfile` (`url`, `aliases`, `industry`, `services`, etc.) and allow inferred profiles to be materialised as ephemeral in-memory profiles and/or written under `pilots/generated/` (or stored as JSON on the `Run`).

**Why:** Minimises schema churn; `execute_run` already consumes `PilotProfile`. A full `Business` table can come when self-serve accounts exist.

**Alternatives:** New SQLite `businesses` table now — deferred as premature for operator URL paste.

### 2. Pipeline order: fetch → extract → enrich → queries → existing `execute_run`

1. Normalise URL; fetch HTML (homepage; optionally 1–2 same-origin links like `/about`, `/services` if linked and cheap)
2. LLM JSON extract: `brand_name`, `aliases`, `location`, `services`, `description`, `competitors` (may be empty)
3. If location/competitors too thin: one search-grounded enrichment call (reuse existing probe providers where practical)
4. Instantiate accountant template queries with `{location}` / service slots; optional small LLM rewrite for natural phrasing
5. Create run with inferred profile; background `execute_run` as today

### 3. Alias matching

Visibility gate: case-insensitive substring match if **any** of `[brand_name] + aliases` appears (apply simple normalisations: strip Ltd/LLP/Limited). Competitors unchanged (list of strings). Extraction prompt uses primary `brand_name` plus aliases for context.

### 4. API shape

- `POST /api/runs/from-url` with `{ "url": "...", "vertical": "accountants" }` (vertical default accountants)
- Returns immediately with `run_id` and `status: running` (inference may run in the same background task before probes, or a short sync infer then async probes — prefer **one background task**: infer then probe so HTTP stays fast)
- Existing `POST /api/runs` with `pilot_id` unchanged

### 5. UI

Minimal: URL text field + “Analyse URL” next to demo pilot flow. Show inferred brand name when poll returns / on completion. No confirm wizard.

### 6. Cost controls

- Cap free/operator URL runs to template query count (≈10) and respect `TYGEO_ENABLED_PROBES` (document recommending 2 models for outreach volume)
- Log `phase: url_fetch`, `phase: profile_extract`, `phase: profile_enrich`, `phase: query_gen` in `usage_log` with costs when LLM used

### 7. Dependencies

- HTTP fetch via `httpx` (or stdlib) with timeout, size limit, basic HTML→text extraction (no headless browser in v1)
- If site blocks bots: enrichment path from domain token + search LLM without HTML body

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Scrape blocked / JS-only sites | Search/LLM enrich fallback from URL/domain; operator can still use YAML gold |
| Wrong brand name / location | Gold fixtures + spot-check; log raw extract JSON on run for debugging |
| Competitor hallucination | Prefer competitors present on-site; mark enrich-sourced competitors in metadata |
| Cost blow-up on 50 URLs | Query×model caps; prefer 2 models for batch outreach |
| Open unauthenticated spend | Operator-only for now; document risk; optional env kill-switch later |
| Alias false positives | Keep aliases short; avoid single generic tokens |

## Migration Plan

- Deploy API with new endpoint; UI behind same Vercel app
- Demo YAML pilots keep working without new fields
- Rollback: disable UI button / route; old `POST /api/runs` unaffected

## Open Questions

- Persist generated profiles to disk vs only on `Run` row metadata for v1? **Default:** store snapshot JSON on the run; optionally write YAML under `pilots/generated/` when `TYGEO_SAVE_GENERATED_PILOTS=1`
- Exact accountant template list — draft in repo during implement; Sam can edit YAML templates without code changes
