# Delta spec: `geo-probe` (change `dashboard-history-view`)

Baseline capability lives in [`../../../specs/geo-probe/spec.md`](../../../specs/geo-probe/spec.md).

## ADDED Requirements

### Requirement: Run history listing

The API MUST expose `GET /api/runs` returning a list of run summaries ordered by `created_at` descending. The endpoint MUST accept optional query parameters `pilot_id` (filter to one pilot) and `limit` (default 20, max 100). Each list item MUST include `id`, `created_at`, `pilot_id`, `brand_name`, `status`, `visibility_rate`, and `total_cost_usd`.

#### Scenario: List runs for a pilot

- **WHEN** the client calls `GET /api/runs?pilot_id=dishoom-london&limit=20`
- **THEN** the API returns only runs for that pilot, newest first, up to the requested limit

#### Scenario: List all recent runs

- **WHEN** the client calls `GET /api/runs` without `pilot_id`
- **THEN** the API returns the most recent runs across all pilots

### Requirement: Dashboard history view

The web dashboard MUST load the most recent **completed** run automatically when the user selects a demo brand, without requiring a new probe run. The dashboard MUST display a visibility trend chart plotting `visibility_rate` (as a percentage) over time for completed runs of the selected brand. The summary panel MUST show the date and time of the loaded run.

#### Scenario: Auto-load latest run on brand select

- **WHEN** the user selects a demo brand that has at least one completed run
- **THEN** the dashboard fetches run history for that `pilot_id` and displays the latest completed run (summary, query table, and replies)

#### Scenario: Trend chart for historical runs

- **WHEN** the user views a brand with multiple completed runs
- **THEN** the dashboard shows a line chart of visibility % by run date for those runs

#### Scenario: No prior runs

- **WHEN** the user selects a brand with no completed runs
- **THEN** the dashboard shows the brand configuration and probe list without summary or chart until the user runs a new analysis

## MODIFIED Requirements

### Requirement: Persistence

The system MUST use SQLite to store runs, per-query rows, and recommendations so results can be retrieved later without re-invoking models. On Railway production deploys, the database file MUST reside on a mounted volume (e.g. `TYGEO_DATABASE_URL=sqlite:////data/tygeo.db`) so run history survives redeploys.

#### Scenario: Fetch historical run

- **WHEN** the client calls `GET /api/runs/{id}` for an existing id
- **THEN** the API returns stored query rows and recommendations without re-running probes

#### Scenario: Production volume persistence

- **WHEN** Railway is configured with a volume at `/data` and `TYGEO_DATABASE_URL=sqlite:////data/tygeo.db`
- **THEN** completed runs remain available after a service redeploy
