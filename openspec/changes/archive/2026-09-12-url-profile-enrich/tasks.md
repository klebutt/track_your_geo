## 1. Enrich gate

- [x] 1.1 Update `infer_pilot_from_url` so competitor/alias enrich runs when those lists are empty after extract (even if brand + location already present)
- [x] 1.2 Merge enrich competitors/aliases into the profile without wiping good extract fields; keep list caps
- [x] 1.3 Ensure `usage_log` still records `profile_enrich` when the gap-fill enrich runs

## 2. Location normalisation

- [x] 2.1 Add primary-location helper for multi-segment location strings
- [x] 2.2 Use primary location for accountant query template fill; retain raw location in snapshot when different

## 3. Tests and record

- [x] 3.1 Add/extend `eval/test_url_intake.py` coverage for: enrich-after-extract when competitors empty; multi-office → primary location in queries
- [x] 3.2 Run `pytest eval -q` and fix regressions
- [x] 3.3 Optional live smoke on one prior URL; note competitor/alias quality in worklog
- [x] 3.4 Update `docs/worklog/` and vault `status.md` / `AGENTS.md` active change
