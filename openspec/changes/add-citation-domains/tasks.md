# Tasks: per-query citation domains

## 1. API extraction and persistence

- [x] 1.1 Add `tygeo.citations` module (`extract_domains`, `classify_cited_domains`)
- [x] 1.2 Add `brand_domains` to pilot model and hardcoded pilots
- [x] 1.3 Add `cited_domains` JSON column + SQLite migration in `init_db`
- [x] 1.4 Wire extraction in `execute_run`; expose on `QueryResultOut` / `PilotDetail`

## 2. Tests

- [x] 2.1 Add `eval/test_citations.py` (extract, classify, empty, markdown links)

## 3. Dashboard

- [x] 3.1 Per-query domain chips in results table and reply details
- [x] 3.2 Remove illustrative `seed_domains` panel; add citations disclaimer copy

## 4. Validation

- [x] 4.1 Run `pytest eval -q`
