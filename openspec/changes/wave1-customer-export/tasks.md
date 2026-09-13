## 1. Plain-report copy locks

- [x] 1.1 Update `_deeper_insights` to take brand name; action-plan title uses firm, not town
- [x] 1.2 Set `index_note` to visibility/position/sentiment/citations compass gloss (no em dashes)
- [x] 1.3 Strip em dashes from customer-facing plain_report strings
- [x] 1.4 Align App.tsx Soft lead-in (drop Soft) and index fallback with locked gloss

## 2. Customer export + PDF

- [x] 2.1 Add `customer_export.py` building customer markdown/HTML (no internal notes / stance codes)
- [x] 2.2 Render PDF via fpdf2; safe `[Firm]-AI-recommend.pdf` names
- [x] 2.3 Add eval tests for copy locks + export omissions

## 3. Wave-1 bulk runner

- [x] 3.1 Script reads vault prospects path; sequential local URL runs; heartbeats
- [x] 3.2 After each firm: PDF, JSONL/CSV append, `wave1-progress.md` update
- [x] 3.3 Pause after first 5 successes; continue on firm fail with exclusion_reason; hard-stop on auth

## 4. Validate and docs

- [x] 4.1 `pytest eval -q`
- [x] 4.2 Hewitt PDF smoke vs Change-now checklist
- [x] 4.3 Vault status + AGENTS + worklog; mark Option A locked
