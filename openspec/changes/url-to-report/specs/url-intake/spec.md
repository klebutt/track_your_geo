## ADDED Requirements

### Requirement: URL-only analysis intake

The system MUST accept a website URL and vertical identifier (default `accountants`) and MUST start an analysis run without requiring multi-field business forms. The system MUST infer a business profile (at minimum `brand_name`, `location`, `aliases`, `competitors`, `queries`) before executing GEO probes. The system MUST NOT require the analysed business to confirm profile fields as part of the happy path.

#### Scenario: Start run from URL

- **WHEN** the client calls `POST /api/runs/from-url` with a valid `http` or `https` URL
- **THEN** the API returns immediately with a run id and `status: running`
- **AND** a background task infers a profile and then executes probes using that profile

#### Scenario: Reject invalid URL

- **WHEN** the client submits a missing or non-http(s) URL
- **THEN** the API responds with `4xx` and does not create a run

### Requirement: Profile inference from website URL

The system MUST attempt to fetch the URL (with timeout and response size limits) and MUST use an LLM structured extraction step to populate profile fields from page text when fetch succeeds. When fetch fails or yields insufficient text, the system MUST attempt a search-grounded or LLM enrichment fallback using the URL/domain so that a best-effort profile can still be produced. Inference token/cost MUST be recorded in `usage_log` with distinct phases for fetch/extract/enrich/query generation as applicable.

#### Scenario: Successful HTML extract

- **WHEN** the homepage HTML is fetched successfully
- **THEN** the system extracts at least `brand_name` and `location` (location MAY be empty if truly unknown) and records extract cost/usage when an LLM is called

#### Scenario: Fetch failure fallback

- **WHEN** the HTTP fetch fails (timeout, block, or empty body)
- **THEN** the system still attempts enrichment from the URL/domain
- **AND** proceeds to probes if a `brand_name` can be inferred
- **AND** records the failure in `usage_log` without aborting the whole run unless no brand name can be inferred

### Requirement: Accountant query generation

For vertical `accountants`, the system MUST build approximately 8–15 brand-neutral customer-intent queries from a template bank combined with inferred location and services. Queries MUST NOT include the target brand name in the prompt text. Other verticals MAY be rejected with `4xx` in this change.

#### Scenario: Generate accountant queries

- **WHEN** a URL run uses vertical `accountants` and a location is available
- **THEN** the inferred profile includes multiple queries that mention the location or service themes without naming the brand

#### Scenario: Unsupported vertical

- **WHEN** the client requests a vertical other than `accountants`
- **THEN** the API responds with `4xx` explaining only `accountants` is supported in this version

### Requirement: Operator URL UI

The web dashboard MUST provide a control to paste a website URL and start analysis without selecting a demo pilot. While the run is in progress, the UI MUST poll for completion using the existing run polling behaviour.

#### Scenario: Analyse from URL in dashboard

- **WHEN** the operator pastes a URL and starts analysis
- **THEN** the client calls `POST /api/runs/from-url` and polls `GET /api/runs/{id}` until the run completes or fails
