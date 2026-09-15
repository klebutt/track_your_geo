# Worklog — 2026-09-15 (batch-40 complete)

## Outcome

Wave-1 **batch-40** finished cleanly after API cleanup:

- **40/40 ok · 0 failed · $26.05 USD** (single `--reuse-completed` runner)
- Runner: `scripts/wave1_batch40_export.py`
- Vault: `reports/wave1-batch40-manifest.csv`, `wave1-batch40-progress.md`, `wave1-batch40-errors.csv`, PDFs in `wave1-pdfs/`
- Cosmetics **QA-10** untouched (do not regenerate)
- Sendable pack target ≈ **50** (QA-10 + batch-40)

## Ops notes

- Dual runners earlier caused TPM contention and timeout pile-up; killed orphans, marked stuck `running` rows failed, restarted uvicorn **without** `--reload`
- Sleep suspends probes — keep PC awake for overnight/day runs
- PDF skip mismatches: copied `Rogove-AI-recommend.pdf` → `Rogove-and-Company-…` and `HB-and-O-…` → `HB-and-O-Accountants-…` so `--reuse-completed` matched URL-list firm names
- Manifest may still have duplicate rows from the dual-runner stretch — dedupe before BD sheets

## Code / docs

- Cosmetics PDF layout in `tygeo/customer_export.py` (hero X of N, snapshot table, page-1 AI Recommend wordmark)
- `AGENTS.md` + vault `status.md` updated to batch-40 complete
