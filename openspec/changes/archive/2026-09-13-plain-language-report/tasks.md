## 1. Report builder

- [x] 1.1 Add a pure helper that builds a plain-language report dict from run query results (unique queries, X/N, win queries, competitor-only queries, optional short gap blurb)
- [x] 1.2 Expose the report on the run API response (e.g. `plain_report` on `RunOut`) without a new LLM call
- [x] 1.3 Unit-test the helper for: all-hit, mixed, zero-visibility, and multi-model same-query aggregation

## 2. Dashboard UI

- [x] 2.1 Add a plain-language report section above technical Summary/Insights when a completed run is loaded
- [x] 2.2 Render headline X/N, wins/losses lists, and light footnote about multi-model probes; keep GEO score in existing sections
- [x] 2.3 Ensure section works for URL-recovered runs and demo brand runs

## 3. Validate and record

- [x] 3.1 Run `pytest eval -q` and fix regressions
- [x] 3.2 Manual UI smoke on a completed local run (Show latest URL analysis)
- [x] 3.3 Update `docs/worklog/` and vault `status.md` / `AGENTS.md`
