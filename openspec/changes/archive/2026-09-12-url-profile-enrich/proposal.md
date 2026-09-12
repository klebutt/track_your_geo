## Why

URL intake often produces empty `competitors` / thin `aliases` and multi-office `location` strings that poison every query template. That undermines the “who you’re losing to” story and local intent quality for the ~50 accountant outreach experiment. Fix inference quality before packaging a plain-language report.

## What Changes

- Always run a competitor/alias enrichment step after homepage extract when those fields are empty (not only when brand/location/scrape is thin).
- Normalise inferred location to a single primary place for query templates (keep fuller location text on the profile if useful).
- Persist enrich phase costs in `usage_log` as today; no new API surface required beyond better `profile_snapshot` contents.
- Keep URL-only intake (no accountant-facing forms). Keep 3-model probe set for outreach.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `url-intake`: Strengthen profile inference so competitors/aliases are populated when scrape alone does not mention them; require primary-location selection for query generation.

## Impact

- Code: `apps/api/tygeo/url_intake.py` (enrich gate, location normalisation, possibly alias generation), tests in `eval/test_url_intake.py`
- API contract: unchanged (`POST /api/runs/from-url`); richer `profile_snapshot`
- Cost: +1 LLM enrich call on most successful scrapes (~small $ vs ~$0.50 full run)
- Out of scope this change: plain-language customer report, Railway/prod deploy, cost caps / query trim
