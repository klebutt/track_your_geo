# Proposal: Generic batch export runner (retroactive)

**Status:** Retroactive documentation — behaviour shipped without an OpenSpec change in October 2026.

## Why

PRs [#3](https://github.com/klebutt/track_your_geo/pull/3), [#9](https://github.com/klebutt/track_your_geo/pull/9), and [#10](https://github.com/klebutt/track_your_geo/pull/10) introduced `scripts/batch_export.py` for wave-2 style batches: vault manifests, URL-normalized resume, manifest dedupe, CSV `location`/`display_name` overrides, regenerate mode, and integration with site build. September `wave1-customer-export` covered a different bulk script (`wave1_bulk_export.py`); this change documents the generic runner.

## What changed (as implemented)

- `scripts/batch_export.py` — probe/regenerate/rerun/skip planner, manifest + run log + errors, `--dedupe-manifest`, `--regenerate` + default rescore.
- `POST /api/runs/from-url` schema — optional `location`, `display_name` (see also `url-intake` spec).

## Capabilities

- New: `batch-export-runner`
- Modified: `url-intake` (operator overrides on from-url)

## Uncertainty

- Wave-1 pause-after-five behaviour remains in `wave1_bulk_export.py` only; not duplicated in `batch_export.py` (documented under `customer-report-export`).
