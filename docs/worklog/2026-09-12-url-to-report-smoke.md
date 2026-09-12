# Worklog — 2026-09-12 (url-to-report smoke)

## Goal

Option A: validate URL → report enough to close Sprint 1 (recover Mpathy, more accountant URLs, decide deploy/archive).

## Recover

- Local API (`8000`) + Vite (`5173`) from repo root; DB `data/tygeo.db`.
- **Show latest URL analysis** loaded run #10 (Mpathy Accounting) correctly: URL filled, ~90% visibility, recommendations intact.

## New smokes (live LLM)

| Run | URL | Brand / location | Vis | Composite | Cost | Notes |
|-----|-----|------------------|-----|-----------|------|-------|
| 10 (prior) | mpathyaccounting.co.uk | Mpathy Accounting / Dulwich | 90% | 79.8 | ~$0.50 | aliases/competitors empty |
| 11 | bennettbrooks.co.uk | Bennett Brooks / Northwich, UK | 50% | 51.0 | $0.49 | scrape OK; empty aliases/competitors |
| 12 | milstedlangdon.co.uk | Milsted Langdon / multi-city string | 40% | 47.5 | $0.56 | location too broad → noisy queries |
| 13 | accountsandlegal.co.uk | Accounts and Legal / United Kingdom | 15% | 27.5 | $0.52 | HEAD was 403; GET still extracted; weak location |

All runs: 5 recommendations; only **Perplexity + Gemini** probe rows (20); **10 `probe_error`** each from OpenAI.

## Quality issues found

1. **OpenAI search deprecated** — `gpt-4o-mini-search-preview` returned 404 on every probe (fixed same day → `gpt-5-search-api`; see `2026-09-12-openai-search-migrate.md`).
2. **Aliases/competitors always empty** when homepage scrape yields name + location — `need_enrich` skips `profile_enrich`; `generate_aliases` only strips Ltd/LLP-style suffixes (none present).
3. **Multi-office locations** (Milsted) get pasted wholesale into every template → weak, non-local queries.
4. **Bot blocks** are common on accountant sites (TaxAssist, Bishop Fleming, Hazlewoods HEAD 403); Accounts and Legal still extracted somehow — enrich fallback not exercised on these runs.
5. **Cost** stable ~$0.49–0.56 per full URL run at current probe set.
6. UI: after URL recover, demo brand section can still show Clio probe list; summary/results correctly show the URL run.

## Deploy / archive decision

- **Deploy:** hold until OpenAI probe model is replaced (or removed from enabled probes); otherwise prod will silently drop 1/3 of probes.
- **Archive `url-to-report`:** ready to archive with follow-ups logged; Sprint 2 should start with model swap + force competitor/alias enrich + primary-location pick.

## Next

1. Fix/replace deprecated OpenAI search probe (config or code).
2. Archive OpenSpec `url-to-report`.
3. Sprint 2: enrich always for competitors/aliases; location normalisation; plain-language report; cost caps (2 models for outreach).
