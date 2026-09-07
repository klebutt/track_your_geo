## Why

The prototype can analyse YAML demo brands but cannot turn a real accountant website into a report without hand-written profiles. For an outreach experiment (~50 firms), the operator needs **URL-only** intake: paste a URL, infer profile and queries, run the existing analysis engine — no forms for accountants.

## What Changes

- Extend pilot/business profile schema with `url`, `aliases`, optional `industry` / `services`, and version metadata used for matching and re-tests
- Alias-aware brand mention matching (substring over primary name + aliases)
- Accountant query **template bank** instantiated from an inferred profile (location/services)
- New **URL → profile** pipeline: fetch site (and cheap enrichment), LLM-extract profile fields, infer competitors when needed, generate queries
- New API (and minimal UI) to start a run from a **website URL** that creates/uses an inferred profile then executes the existing probe → score → recommendations path
- Gold fixture(s) for 1–2 accountant URLs to calibrate extraction (manual YAML OK)
- Cost logging for scrape/enrich/extract steps in `usage_log`
- Deterministic tests with mocked fetch/LLM (no live scrape in default pytest)

## Capabilities

### New Capabilities

- `url-intake`: Accept a website URL, infer a business profile and customer-intent query set (accountants vertical for v1), and start an analysis run without multi-field forms

### Modified Capabilities

- `geo-probe`: Pilot profiles MAY include `url`, `aliases`, and related fields; brand visibility matching MUST consider aliases; runs MAY be started from an inferred URL-based profile in addition to selecting a static YAML pilot

## Impact

- **API:** New endpoint(s) for URL intake / URL-started runs; existing `POST /api/runs` with `pilot_id` remains
- **Core:** `pilots.py` schema, mention matching in `analysis.py`, new inference module(s), possibly HTTP fetch dependency
- **UI:** Minimal URL field alongside (or above) demo pilot picker for operator use
- **Cost:** Extra LLM (and optional search) calls per URL before probes; must be logged and kept small vs full multi-model runs
- **Ops:** No auth yet — URL intake can spend money; operator-only use for the experiment is acceptable with cost caps / query×model limits documented
