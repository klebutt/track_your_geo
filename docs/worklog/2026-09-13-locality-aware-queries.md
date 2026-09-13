# Worklog — 2026-09-13 (locality-aware-queries)

## Decisions locked

1. `local_primary`: up to **2** national niche queries (8 local + 2 national)
2. `hybrid`: **~30%** UK-wide (**7 + 3**)
3. Stance via **cheap LLM fields** on extract/enrich

Also: `local_only` 10+0; `remote_primary` 3+7; `unclear` → local_primary mix.

## Shipped

- Archived `plain-language-report` → `openspec/changes/archive/2026-09-13-plain-language-report/`
- OpenSpec **locality-aware-queries** proposed + implemented:
  - `locality_stance` / `online_remote` on extract & enrich
  - Template banks `local` / `national` in `accountants_queries.yaml`
  - Mix-by-stance query builder; stance-aware competitor enrich
  - Snapshot fields + plain-report `geography_note` in UI
- **68** tests passed

## Next

- Archive `locality-aware-queries` after one live Top-10 URL smoke (optional)
- Start Top 10 from vault `accountant-prospects` (do not copy list into git)
- Railway remains parked
