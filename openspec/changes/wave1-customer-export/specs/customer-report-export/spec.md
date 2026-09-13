## ADDED Requirements

### Requirement: Customer PDF export

The system MUST be able to produce a customer-facing AI Recommend PDF for a completed analysis run. The PDF filename MUST be of the form `[Firm]-AI-recommend.pdf` (filesystem-safe firm segment). The customer export MUST omit operator-only content including internal cost notes and locality stance codes such as `local_primary`.

#### Scenario: Export omits locality jargon

- **WHEN** a customer PDF is generated for a run that has an inferred locality stance code
- **THEN** the customer PDF body does not include raw stance tokens such as `local_primary`, `hybrid`, or `remote_primary`
- **AND** plain-English geography footnotes MAY still appear

#### Scenario: Filename uses firm name

- **WHEN** a customer PDF is exported for firm “Hewitt Accountancy”
- **THEN** the file is named `Hewitt Accountancy-AI-recommend.pdf` (or an equivalent sanitized variant preserving the firm identity)

#### Scenario: Who showed up keeps queries

- **WHEN** the customer PDF includes competitor contrast for losses
- **THEN** each listed loss retains the specific query text (Hewitt / dashboard shape)

### Requirement: Wave-1 bulk handoff artifacts

A local bulk runner MUST read prospect URLs from a vault path supplied at runtime (MUST NOT require committing the prospect list into git), generate customer PDFs into a vault output folder, append one log line per firm as each completes (CSV or JSONL), and update a live vault progress file after every firm with counts, current firm, last success/fail, spend so far, and ETA. After the first five successful completions, the runner MUST pause for operator confirmation before continuing unless explicitly configured to skip the pause. Per-firm failures MUST be logged with an exclusion reason and MUST NOT halt the batch unless authentication or provider credentials are broken.

#### Scenario: Mid-run progress is usable

- **WHEN** the bulk runner finishes firm N of the batch
- **THEN** the progress file reflects N done / total, last outcome, spend so far, and ETA
- **AND** the run log has one additional line for that firm

#### Scenario: First-five pause

- **WHEN** five firms have completed successfully and pause-after is enabled
- **THEN** the runner waits for operator continue before starting firm six

#### Scenario: Firm failure continues

- **WHEN** a single firm fails for a non-auth reason
- **THEN** the log records `exclusion_reason`
- **AND** the runner proceeds to the next firm
