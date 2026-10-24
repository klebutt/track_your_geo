# Worklog — 2026-10-24 (batch export runner)

## Outcome

Generic batch report runner created for wave-2 and future batches:

- **New script:** `scripts/batch_export.py` — reuses logic from `wave1_batch40_export.py`
- **CTA updated:** "Reply if any of these would help." → book-a-call text with calendar link
- **Tests added:** Deterministic tests for dry-run, CSV parsing, manifest schema, CTA text
- **README section:** "Generating a batch of reports" with exact PowerShell commands

## Changes

### scripts/batch_export.py

Generic batch runner with args:
- `--batch <name>` — e.g. wave2 (determines output folder names)
- `--input <path>` — CSV with `firm_name,url` columns
- `--vault` — default `G:\My Drive\Obsidian\projects\track-your-geo`
- `--base-url` — default `http://127.0.0.1:8000`
- `--limit`, `--offset` — for partial runs
- `--reuse-completed` — skip existing PDFs (default: True)
- `--force` — regenerate even if PDF exists
- `--dry-run` — show plan without running probes

**Key differences from wave1_batch40_export.py:**
- Uses `firm` column (not `firm_name`) for build.py compatibility
- Adds `status` column to manifest for build.py filtering
- Preflight check before starting (API health + cost estimate)
- Dry-run mode shows estimated cost/time

### apps/api/tygeo/plain_report.py

CTA changed from:
> Reply if any of these would help.

To:
> Want to talk it through? Book a free 15-minute call: {BOOKING_LINK}, or just reply to this email.

BOOKING_LINK sourced from `site/config.py` with fallback for standalone API.

### Tests (eval/test_batch_export.py)

- CSV parsing with both `firm_name` and `firm` columns
- Manifest schema validation (has `firm`, `status`, `report_path` for build.py)
- Dry-run mode returns exit 0 without API calls
- Preflight check behavior
- CTA text contains booking link, no prices
- BOOKING_LINK matches site/config.py

## Wave-2 command

```powershell
# Dry run first:
.\tygeo-venv\Scripts\python.exe scripts/batch_export.py `
    --batch wave2 `
    --input "G:\My Drive\Obsidian\projects\track-your-geo\reports\wave2-urls.csv" `
    --dry-run

# Full run:
.\tygeo-venv\Scripts\python.exe scripts/batch_export.py `
    --batch wave2 `
    --input "G:\My Drive\Obsidian\projects\track-your-geo\reports\wave2-urls.csv"
```

## Input CSV format

```csv
firm_name,url
"Example Accountants Ltd","https://example-accountants.co.uk"
"Test & Partners","https://testandpartners.example"
```

## Cost estimate

~$0.65/firm, ~15 min/firm (3-model probes with OpenAI search TPM pacing).

## Not changed

- `scripts/wave1_batch40_export.py` — left intact for reference
- `site/build.py` — already expects `firm` + `status` columns, no changes needed
