## Why

Wave-1 WTP outreach needs ~50 customer PDFs under locked Option A (full 3-model). Sales Change-nows must land in the customer export before overnight generation — current copy still uses town in the action-plan CTA, “Soft” on the £5–20 line, em dashes, vague composite gloss, and locality jargon that should not reach accountants.

## What Changes

- Lock Sales-approved customer-facing strings in `plain_report` (and matching UI Soft/gloss lines) from Hewitt-derived Change-nows
- Add a customer export path that renders AI Recommend PDF (`[Firm]-AI-recommend.pdf`) without internal notes or locality codes
- Add a local bulk runner that reads vault prospect URLs (path args only; never commit the list), runs sequential 3-model URL→report, writes PDFs + manifest, and maintains live vault progress / JSONL mid-run
- First-5 pause for Product Analyst sniff; per-firm failures logged and skipped unless auth/OpenAI is hard-broken

## Capabilities

### New Capabilities

- `customer-report-export`: Customer-facing markdown/HTML → PDF export and wave-1 bulk handoff artifacts (manifest, progress file)

### Modified Capabilities

- `plain-language-report`: Deeper-insights CTA uses firm name; £5–20 line drops “Soft”; composite gloss names visibility/position/sentiment/citations; no em dashes in customer copy; locality stance codes stay out of customer-facing report surfaces used for export

## Impact

- `apps/api/tygeo/plain_report.py`, new export module, `eval/` tests, dashboard Soft/index copy in `App.tsx`
- Ops script under `scripts/` writing only to vault paths supplied at runtime
- PDF generation dependency (light HTML→PDF)
- Vault outputs: `reports/wave1-pdfs/`, `reports/wave1-progress.md`, run log — not git
