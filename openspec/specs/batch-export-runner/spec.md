# Capability: Batch export runner

## Purpose

Operator script `scripts/batch_export.py` to run many URL-based probe batches, export customer PDFs into the vault, maintain manifests for `site/build.py`, and support resume, regenerate, and rescore without committing prospect data to git.

## Requirements

### Requirement: Vault output layout

For a batch name `{batch}`, the runner MUST write under the vault `reports/` folder: `{batch}-manifest.csv`, `{batch}-errors.csv`, `{batch}-progress.md`, `{batch}-pdfs/` (PDF + markdown + `.run.json`), and `{batch}-run-log.jsonl` with per-firm probe metadata including `run_id`.

#### Scenario: Manifest row on success

- **WHEN** a firm completes probing and export successfully
- **THEN** the manifest gains or replaces a row with `firm`, `url`, `report_path`, `generated_at`, `run_cost_gbp`, `sha256`, and `status=ok`

### Requirement: Input CSV schema

The input CSV MUST accept columns `firm_name` (or `firm`), `url`, optional `location`, and optional `display_name`. Rows MUST require a non-empty firm and an `http` or `https` URL.

#### Scenario: Display name on manifest only

- **WHEN** a row includes `display_name`
- **THEN** the manifest `firm` column uses the display name for site/PDF labeling
- **AND** `POST /api/runs/from-url` receives `display_name` in the JSON body when probing

#### Scenario: Location override triggers rerun

- **WHEN** reuse-completed would skip a URL but the CSV `location` differs from the stored `profile_location` in the run log
- **THEN** the planner chooses `rerun` and starts a new probe with the override location

### Requirement: URL-normalized completion detection

With `--reuse-completed` (default on), a firm MUST be skipped when the manifest already has `status=ok` for the same normalized URL (lowercase host, no `www`, no trailing slash, scheme ignored) AND the PDF at `report_path` still exists. Deleting the PDF MUST force a new run. Replacing a manifest row MUST key on normalized URL, not firm name spelling.

#### Scenario: Name mismatch still skips

- **WHEN** the CSV firm label differs from a prior manifest row but the URL matches and the PDF exists
- **THEN** the job is skipped as already complete

### Requirement: Manifest deduplication

`--dedupe-manifest` MUST collapse an existing manifest to one row per normalized URL, keeping the most recent `ok` row when any exist, otherwise the last row for that URL.

#### Scenario: Dedupe after duplicate reruns

- **WHEN** dedupe runs on a manifest with two `ok` rows for the same URL
- **THEN** only the later `ok` row remains

### Requirement: Regenerate without probes

`--regenerate` MUST re-render PDFs (and markdown sidecars) from the latest `run_id` per URL in `{batch}-run-log.jsonl` without calling probe providers. By default it MUST `POST /api/runs/{id}/rescore` before export to recompute mention flags from stored reply text; `--no-rescore` MUST skip that step. Regenerate MUST require the local API to be reachable.

#### Scenario: Dry-run rescore preview

- **WHEN** dry-run regenerate runs with rescore enabled and the API is up
- **THEN** each firm line includes a preview of whether visibility/composite would change

#### Scenario: Regenerate without run log entry

- **WHEN** regenerate is requested but no `run_id` exists for the URL in the run log
- **THEN** the planner falls back to `probe` or reports that a probe is required

### Requirement: Job planning labels

Dry-run and live batch output MUST classify each firm as one of `SKIP`, `PROBE`, `RERUN`, or `REGENERATE` with a human-readable reason.

#### Scenario: Force reprobe

- **WHEN** `--force` is passed without regenerate mode
- **THEN** every firm is planned as `PROBE` even if a PDF exists

### Requirement: Auth failure stops batch

When a failure message indicates missing or invalid provider credentials, the batch MUST stop rather than continuing to burn partial failures.

#### Scenario: Continue on single firm errors

- **WHEN** one firm fails for a non-auth reason
- **THEN** the error is recorded in `{batch}-errors.csv` and processing continues
