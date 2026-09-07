## 1. Schema and matching

- [x] 1.1 Extend `PilotProfile` with optional `url`, `aliases`, `industry`, `services` (and keep existing fields)
- [x] 1.2 Update mention matching so `brand_mentioned` is true if `brand_name` or any alias matches (case-insensitive); add unit tests
- [x] 1.3 Persist inferred profile snapshot on the run (source URL, brand, aliases, competitors, queries) for URL-started runs

## 2. Accountant templates and gold fixtures

- [x] 2.1 Add accountant query template bank (YAML or module) with `{location}` / service placeholders; brand-neutral
- [x] 2.2 Add 1–2 gold accountant pilot YAML fixtures for calibration (manual profiles)

## 3. URL → profile inference

- [x] 3.1 Implement HTML fetch with timeout + size limit and basic HTML-to-text extraction
- [x] 3.2 Implement LLM JSON profile extract (+ usage_log phase); search/LLM enrich fallback when fetch is thin/fails
- [x] 3.3 Generate queries from accountant templates + inferred fields; reject non-`accountants` vertical with 4xx
- [x] 3.4 Wire inference costs into run `total_cost_usd` / `usage_log`

## 4. API and run orchestration

- [x] 4.1 Add `POST /api/runs/from-url` that returns immediately and runs infer→`execute_run` in a background task
- [x] 4.2 Ensure existing `POST /api/runs` with `pilot_id` still works unchanged
- [x] 4.3 Add API tests with mocked fetch/LLM (no live network in default pytest)

## 5. Operator UI

- [x] 5.1 Add URL input + “Analyse URL” control to the dashboard
- [x] 5.2 Poll `GET /api/runs/{id}` using existing progress UX; show inferred brand when available

## 6. Validate and record

- [x] 6.1 Run `pytest eval -q` and fix regressions
- [x] 6.2 Manual smoke: one real accountant URL (note cost) — deferred to operator (needs live keys + real URL); mocked path covered in tests
- [x] 6.3 Update `docs/worklog/` and vault `status.md`; set `AGENTS.md` active change when applying
