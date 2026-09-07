# Worklog — 2026-09-07 (url-to-report)

## Shipped

OpenSpec **url-to-report** implemented and validated locally:

- `PilotProfile` extended with `url`, `aliases`, `industry`, `services`
- Alias-aware visibility matching
- Accountant query templates + gold fixtures under `apps/api/pilots/`
- `tygeo/url_intake.py`: fetch → LLM extract → enrich fallback → query gen
- `POST /api/runs/from-url` (vertical `accountants` only); run stores `source_url` + `profile_snapshot`
- Dashboard: URL field + Analyse URL + **Show latest URL analysis** (recover finished runs)
- UI fix: finishing a URL run no longer gets overwritten by demo-brand history reload
- Tests: `eval/test_url_intake.py`, alias + from-url API coverage; **57 passed**

## Local smoke (Mpathy)

- URL: `https://mpathyaccounting.co.uk/`
- Run #10: brand **Mpathy Accounting**, location Dulwich SE London
- Visibility ~90%, composite ~79.8, ~$0.50, 5 recommendations
- Empty aliases/competitors (enrich skipped when name+location already present)
- ~10 probe_errors (likely one model / Gemini quota) with 20 successful probes

## Next session (continue testing)

1. Confirm UI shows Mpathy via **Show latest URL analysis** after pull
2. Try 2–3 more accountant URLs; note inference quality (aliases, competitors, location)
3. Decide whether to force competitor enrich even when location is present
4. Optional: deploy to Railway/Vercel so prod matches local
5. Archive OpenSpec `url-to-report` when happy with smoke
6. Then Sprint 2: harden scrape + plain-language report + cost caps for ~50 outreach

## Follow-ups (not blocking test)

- Competitor/alias enrichment gap
- Cost caps / 2-model default for batch outreach
- Prod deploy of this branch
