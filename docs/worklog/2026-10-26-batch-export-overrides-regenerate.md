# Batch export: CSV overrides, regenerate, report polish

## Shipped

- Optional CSV columns `location` and `display_name` in `scripts/batch_export.py`.
- `--regenerate` re-renders PDFs from `reports/<batch>-run-log.jsonl` run IDs (no probes).
- Location override triggers automatic **rerun** when it differs from the logged `profile_location`.
- Inferred locations normalized toward `Town, UK` via `normalize_uk_location()` (England/South Wales → UK suffix).
- API `POST /api/runs/from-url` accepts `location` and `display_name`.
- Report polish: ChatGPT search label, all-wins competitor copy, prose brand punctuation, Snapshot page-break grouping.
- **Display vs matching:** `display_name` is export-only; probes use inferred `brand_name` + aliases.

## Validation

- `pytest eval/test_batch_export.py eval/test_plain_report.py eval/test_url_intake.py` (targeted) — pass.
