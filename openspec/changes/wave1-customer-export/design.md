## Context

Option A locked for wave-1: full 3-model URL→report for ~50 vault accountants, local API only, ~$45 / ~12–15h. Sales Change-nows (Hewitt-derived) must ship in the customer PDF before overnight. Railway parked; prospect list stays vault-only.

## Goals / Non-Goals

**Goals:**
- Wire locked customer copy into `plain_report` + matching UI Soft/gloss lines
- Export customer PDF without internal notes or locality stance codes
- Monitored sequential bulk runner writing vault PDFs, progress, and mid-run JSONL/CSV
- Pause after first 5 completions for Product Analyst sniff

**Non-Goals:**
- Probe/scoring/model-mix changes; gpt-5-mini swap; Railway deploy
- Committing `accountant-prospects` or generated PDFs into git
- Email/AgentMail send

## Decisions

1. **Copy source of truth:** `plain_report.py` owns customer strings; UI Soft line and index fallback match. Soft line = Hewitt wording with “Soft ” removed. Action-plan title uses `brand_name`. Index note lists visibility, position, sentiment, citations. Replace U+2014 em dashes with ASCII ` - ` / commas in customer strings only (probe templates may keep em dashes internally; export sanitizes display queries if needed).

2. **Export shape:** Build customer markdown from run + plain_report (60s hierarchy matching Hewitt sample), then PDF via **fpdf2** (pure-Python, Windows-friendly). Optional `.md` sibling for BD. Filename: sanitize firm → `[Firm]-AI-recommend.pdf`.

3. **Bulk runner:** `scripts/wave1_bulk_export.py` takes `--vault`, `--prospects`, `--out`, `--limit`, `--pause-after 5`. Reads URLs from vault markdown tables; calls local `/api/runs/from-url` (or equivalent); polls until complete; writes PDF + appends JSONL; updates `wave1-progress.md` every firm; touches `status.md` every 5 or on failure. Failures → `exclusion_reason`, continue. Hard stop only on auth/429-storm / missing keys pattern.

4. **Customer vs operator:** Export omits Internal notes, locality stance codes, competitor-check lists used for operators. Keeps geography_note if plain English (no `local_primary`). Who-showed-up uses `loss_entries` with query text.

## Risks / Trade-offs

- [Overnight API flake] → per-firm continue + exclusion log; hard-stop only on auth
- [PDF dependency install] → `fpdf2` in requirements; fail clearly if missing
- [Firm name filesystem] → sanitize `/\:*?"<>|` and collapse whitespace
- [First-5 pause forgotten] → default `--pause-after 5`; require `--continue` or Enter to proceed

## Migration Plan

Ship copy + export + script locally; regenerate Hewitt PDF for Sales lock check; then overnight with progress file. No prod migration.

## Open Questions

- None blocking; Soft-line = Hewitt minus “Soft” unless founders override mid-run.
