# Capability: Customer report export

## Purpose

Produce customer-facing AI Recommend PDF and markdown exports from completed probe runs, with operator-only content stripped and filenames safe for handoff. PDF layout uses shared AI Recommend branding (see also snapshot table and booking CTA requirements in this capability).

## Requirements

### Requirement: Customer PDF export

The system MUST be able to produce a customer-facing AI Recommend PDF for a completed analysis run. The PDF filename MUST be of the form `[Firm]-AI-recommend.pdf` where the firm segment is filesystem-safe via `safe_firm_filename`. The customer export MUST omit operator-only content including internal cost notes and raw locality stance codes such as `local_primary`.

#### Scenario: Export omits locality jargon

- **WHEN** a customer PDF is generated for a run that has an inferred locality stance code
- **THEN** the customer PDF body does not include raw stance tokens such as `local_primary`, `hybrid`, or `remote_primary`
- **AND** plain-English geography footnotes MAY still appear when `geography_note` does not contain stance codes

#### Scenario: Filename uses firm name

- **WHEN** a customer PDF is exported for firm "Riverside Accountants"
- **THEN** the file is named `Riverside Accountants-AI-recommend.pdf` (or an equivalent sanitized variant preserving the firm identity)

#### Scenario: Who showed up keeps queries

- **WHEN** the customer PDF includes competitor contrast for losses
- **THEN** each listed loss retains the specific query text

### Requirement: Customer-facing display name

Customer PDF and markdown exports MUST use `profile_snapshot.display_name` as the visible firm label when set; otherwise they MUST use stored `brand_name`. `display_name` MUST affect customer-facing copy only and MUST NOT replace the probe `brand_name` used for matching unless also present in aliases or matching alias expansion.

#### Scenario: Display name on PDF title block

- **WHEN** a run snapshot includes `display_name: "Riverside & Co"` and `brand_name` is the legal entity name
- **THEN** the PDF title block and filename use "Riverside & Co"

### Requirement: Branded PDF header and footer

Customer PDFs MUST render on every page an AI Recommend wordmark header (mark + "AI Recommend" label) and the customer firm name right-aligned, separated by a horizontal rule. The footer MUST show the site domain (`airecommend.co.uk`) as a link on the left and "Page N of M" on the right, separated from body content by a horizontal rule.

#### Scenario: Header on multi-page export

- **WHEN** a customer PDF spans more than one page
- **THEN** each page includes the branded header and footer

### Requirement: Report date on PDF cover

The PDF cover block MUST show a human-readable report date. When `_report_export_date` is set on the run (for example after regenerate export), that timestamp MUST be used; otherwise the run `created_at` (or equivalent run date fields) MUST be used. The date MUST be formatted as day + full month name + year (for example "27 October 2026").

#### Scenario: Regenerate uses export date

- **WHEN** `prepare_run_for_customer_export` sets `_report_export_date` during regenerate
- **THEN** the PDF cover shows that export date rather than the original probe date

### Requirement: Sample report callout

When the run includes `_sample_banner`, the PDF MUST show a tinted callout box with the banner text before the main "what this is" copy, and MUST NOT duplicate the banner inside the body paragraph when the callout is shown.

#### Scenario: Fictional sample report

- **WHEN** the riverside-accountants fixture sample is built with `_sample_banner`
- **THEN** the PDF shows the callout and labels the report as demonstration-only fiction

### Requirement: Snapshot table visibility wording

The customer PDF snapshot table MUST label the visibility row **Mentioned in AI replies** with a value of the form `{percent}% of replies`, reflecting the fraction of stored per-model probe rows where the brand was mentioned (not unique-query recommend rate).

#### Scenario: Snapshot distinguishes reply rate from X of N hero

- **WHEN** a run has multiple models per query
- **THEN** the hero block still shows X of N unique queries recommended
- **AND** the snapshot row shows per-reply mention percentage

### Requirement: Booking CTA in customer copy

Customer markdown and PDF deeper-insights sections MUST include a deterministic booking CTA pointing at `https://airecommend.co.uk/book` (short link) and contact email `kieran@airecommend.co.uk`, without listing probe prices.

#### Scenario: Deeper insights lead-in

- **WHEN** a customer export includes optional deeper next steps
- **THEN** the lead-in invites a free 15-minute call via `/book` or email

### Requirement: Export sidecar for web rebuild

When markdown export is enabled, the exporter MUST write a `.run.json` sidecar next to the `.md` file containing a JSON snapshot sufficient to rebuild `/r/<slug>/` pages without re-probing (`web_run_snapshot`).

#### Scenario: Batch handoff writes sidecar

- **WHEN** `export_customer_report` writes markdown for a completed run
- **THEN** a `.run.json` file exists alongside the markdown with query results and scores

### Requirement: Wave-1 bulk vault inputs

The `scripts/wave1_bulk_export.py` runner MUST read prospect URLs from a vault path supplied at runtime and MUST NOT require committing the prospect list into git.

#### Scenario: Vault-only prospect list

- **WHEN** wave-1 bulk export runs
- **THEN** input URLs are read from the vault path argument only

### Requirement: Wave-1 bulk progress artifacts

The wave-1 bulk runner MUST generate customer PDFs into a vault output folder, append one log line per firm as each completes (CSV or JSONL), and update a live vault progress file after every firm with counts, current firm, last success/fail, spend so far, and ETA.

#### Scenario: Mid-run progress is usable

- **WHEN** the bulk runner finishes firm N of the batch
- **THEN** the progress file reflects N done / total, last outcome, spend so far, and ETA
- **AND** the run log has one additional line for that firm

### Requirement: Wave-1 first-five pause

After the first five successful completions, the wave-1 bulk runner MUST pause for operator confirmation before continuing unless explicitly configured to skip the pause.

#### Scenario: First-five pause

- **WHEN** five firms have completed successfully and pause-after is enabled
- **THEN** the runner waits for operator continue before starting firm six

### Requirement: Wave-1 per-firm failure handling

Per-firm failures in wave-1 bulk export MUST be logged with an exclusion reason and MUST NOT halt the batch unless authentication or provider credentials are broken.

#### Scenario: Firm failure continues

- **WHEN** a single firm fails for a non-auth reason
- **THEN** the log records `exclusion_reason`
- **AND** the runner proceeds to the next firm
