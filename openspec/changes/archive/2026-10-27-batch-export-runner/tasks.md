## 1. Runner

- [x] 1.1 Add `scripts/batch_export.py` with vault layout and manifest fields
- [x] 1.2 URL-normalized completion index and `--force` / `--reuse-completed`
- [x] 1.3 `--dedupe-manifest` command

## 2. Overrides and modes

- [x] 2.1 CSV `location` and `display_name` columns; rerun on location change
- [x] 2.2 `--regenerate` from run log + optional rescore
- [x] 2.3 Dry-run action labels (SKIP/PROBE/RERUN/REGENERATE)

## 3. API

- [x] 3.1 Extend from-url body with `location` and `display_name`

## 4. Specs (retroactive)

- [x] 4.1 Add `openspec/specs/batch-export-runner/spec.md`
- [x] 4.2 Update `openspec/specs/url-intake/spec.md` overrides section
