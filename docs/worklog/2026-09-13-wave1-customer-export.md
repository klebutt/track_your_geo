# Worklog — 2026-09-13 (wave-1 customer export + Option A)

## Decision

Option A locked: full 3-model × ~50, local API, ~$45 / ~12–15h. Keep `gpt-5-search-api`.

## Shipped (`wave1-customer-export`)

- Sales Change-nows in `plain_report` + UI: firm CTA (not town), no Soft, plain composite gloss, £5-20, no em dashes, query-level losses
- `tygeo/customer_export.py` → hyphenated `[Firm]-AI-recommend.pdf` (+ .md); rendered markdown (fpdf2); customer model labels only
- Fix: empty-loss `competitor_summary` no longer duplicated in Who-showed-up
- `scripts/wave1_bulk_export.py`: vault prospects path, progress, JSONL/CSV, fail-continue
- Dep: `fpdf2` (+ `pypdf` for export tests)

## Also same day (related)

- Locality-aware queries, report-conversion-quickwins, OpenAI probe pace/retry, past URL runs dropdown
- OpenSpec: `locality-aware-queries`, `report-conversion-quickwins`, `wave1-customer-export`; plain-language-report archived under `openspec/changes/archive/`

## Wave-1 check batch (done)

First 5 (`--limit 5 --reuse-completed`): 5/5 ok · ~$3.66  
Mpathy 7/10 · Hewitt skipped · Simon 6/10 · Gilchrist 4/10 · Fox 6/10

## Overnight remainder → superseded by batch-40

Original plan (`wave1_bulk_export.py --offset 5 --limit 45`) was replaced by cosmetics QA-10 + named **batch-40** URL list.

**Done 2026-09-15:** see [2026-09-15-batch40-complete.md](2026-09-15-batch40-complete.md) — 40/40 · $26.05 · `scripts/wave1_batch40_export.py`.

Vault: `reports/wave1-pdfs/`, `cosmetics-qa-10-manifest.csv`, `wave1-batch40-manifest.csv`, `wave1-batch40-progress.md`
