## 1. Stance and templates

- [x] 1.1 Add `locality_stance` / `online_remote` to extract (+ enrich) JSON prompts and normalise allowed values
- [x] 1.2 Split accountant templates into local vs national banks; keep ~10-query budget
- [x] 1.3 Implement mix-by-stance helper with locked counts (local_only 10/0, local_primary 8/2, hybrid 7/3, remote_primary 3/7, unclear→local_primary)

## 2. Competitors, snapshot, report

- [x] 2.1 Branch competitor enrich prompt by stance (local-first for local_* )
- [x] 2.2 Persist stance fields on PilotProfile snapshot
- [x] 2.3 Add `geography_note` to plain_report from stance; show in dashboard

## 3. Validate and record

- [x] 3.1 Unit tests for mix counts and stance normalisation
- [x] 3.2 `pytest eval -q`
- [x] 3.3 Update worklog + vault status / AGENTS.md
