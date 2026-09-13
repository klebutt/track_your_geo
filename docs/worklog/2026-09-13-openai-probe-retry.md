# Worklog — 2026-09-13 (OpenAI probe rate-limit retry)

## Problem

Outreach runs finished **22/30** probes; **8** `gpt-5-search-api` failures were OpenAI **6000 TPM** rate limits with no retry.

## Fix

In `apps/api/tygeo/analysis.py`:

- Retry rate-limit / 429 up to **6** attempts; on 429 sleep `max(45s, 15s×attempt)` up to **90s** (also honors provider “try again in …” hints)
- Pace OpenAI search probes by **~35s** between `gpt-5-search-api` calls

## Validation

- Unit: `eval/test_probe_retry.py` (7 passed)
- Prior (shorter backoff): Alera #23 / MCC #24 — **28/30** each
- MCO Accountancy #25 (final settings): **30/30**, **0** probe_errors, OpenAI **10/10**, ~15 min wall clock, ~$0.89 — **pass**

## Note

Runs are slower under the 6k TPM tier (pace + retries). Prefer that over silent 8-drop OpenAI gaps for outreach packs.

Bulk ~50 planning numbers and BD/Sales options: vault `decisions/2026-09-13-bulk-probe-economics.md` · repo `docs/worklog/2026-09-13-bulk-probe-economics.md`.
