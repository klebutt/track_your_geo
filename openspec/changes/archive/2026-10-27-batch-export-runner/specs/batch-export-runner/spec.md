## ADDED Requirements

### Requirement: Vault output layout

For a batch name `{batch}`, the runner MUST write under the vault `reports/` folder: manifest, errors, progress, PDF folder, and JSONL run log with `run_id` per URL.

#### Scenario: Manifest row on success

- **WHEN** a firm completes probing and export successfully
- **THEN** the manifest records `status=ok` with `sha256` of the PDF

### Requirement: URL-normalized completion detection

The runner MUST skip completed firms by normalized URL when the manifest PDF still exists, and MUST replace rows by URL not firm label spelling.

#### Scenario: Name mismatch still skips

- **WHEN** the CSV firm label differs from a prior manifest row but the URL matches and the PDF exists
- **THEN** the job is skipped as already complete

### Requirement: Regenerate without probes

`--regenerate` MUST re-export from stored `run_id` values and by default rescore via the local API before PDF generation.

#### Scenario: Dry-run rescore preview

- **WHEN** dry-run regenerate runs with rescore enabled and the API is up
- **THEN** each firm line includes whether scores would change
