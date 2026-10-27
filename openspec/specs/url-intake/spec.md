# url-intake Specification

## Purpose

URL-only business intake for GEO analysis: fetch/infer a profile from a website URL (accountants vertical), generate brand-neutral queries, and start a probe run without multi-field forms.
## Requirements
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

The system MUST attempt to fetch the URL (with timeout and response size limits) and MUST use an LLM structured extraction step to populate profile fields from page text when fetch succeeds.

#### Scenario: Successful HTML extract

- **WHEN** the homepage HTML is fetched successfully
- **THEN** the system extracts at least `brand_name` and `location` (location MAY be empty if truly unknown) and records extract cost/usage when an LLM is called

#### Scenario: Fetch failure fallback

- **WHEN** the HTTP fetch fails (timeout, block, or empty body)
- **THEN** the system still attempts search-grounded or LLM enrichment from the URL/domain
- **AND** proceeds to probes if a `brand_name` can be inferred
- **AND** records the failure in `usage_log` without aborting the whole run unless no brand name can be inferred
- **AND** records inference token/cost in `usage_log` with distinct fetch/extract/enrich phases when LLMs run

### Requirement: Competitor and alias enrichment

After extract (and any thin-page brand/location enrich), if `competitors` is empty or `aliases` is empty (after deterministic alias generation), the system MUST run an enrichment step to populate competitor and/or alias lists when reasonably possible for the vertical and location. Enrichment MUST NOT be skipped solely because `brand_name` and `location` were already present from the homepage extract.

#### Scenario: Competitor enrich after successful extract

- **WHEN** homepage extract yields a brand name and location but an empty competitors list
- **THEN** the system runs an enrichment step that attempts to populate competitors
- **AND** records the enrich call in `usage_log`
- **AND** the profile snapshot used for the run includes any competitors returned (capped)

### Requirement: Multi-office location normalization

When the inferred location string names multiple places (e.g. a comma-separated office list), the system MUST derive a single primary location for accountant query template fill. The profile snapshot MUST still expose enough location detail for operator review (primary location required; fuller raw location MAY be retained when it differs).

#### Scenario: Multi-office location normalised for queries

- **WHEN** the inferred location string contains multiple comma-separated places
- **THEN** query templates are filled with a single primary location
- **AND** the profile snapshot retains enough information for an operator to see the broader location context when it differed from the primary

### Requirement: Locality stance on profile snapshot

For vertical `accountants`, the system MUST infer a `locality_stance` of `local_only`, `local_primary`, `hybrid`, `remote_primary`, or `unclear` from site signals during extract and/or enrich. Cloud accounting software alone MUST NOT force `hybrid`; UK-wide or remote-client claims MAY. The profile snapshot MUST include `locality_stance`. Competitor enrichment MUST prefer local/regional rivals when stance is `local_only` or `local_primary`.

#### Scenario: Locality stance persisted

- **WHEN** URL intake completes profile inference for accountants
- **THEN** the profile snapshot includes a `locality_stance` value from the allowed taxonomy

### Requirement: Accountant query generation

For vertical `accountants`, the system MUST build approximately 8–15 brand-neutral customer-intent queries from template banks combined with inferred location, services, and `locality_stance`. Queries MUST NOT include the target brand name in the prompt text. Other verticals MAY be rejected with `4xx`.

#### Scenario: Generate accountant queries

- **WHEN** a URL run uses vertical `accountants` and a location is available
- **THEN** the inferred profile includes multiple queries that mention the location or service themes without naming the brand

#### Scenario: Unsupported vertical

- **WHEN** the client requests a vertical other than `accountants`
- **THEN** the API responds with `4xx` explaining only `accountants` is supported in this version

### Requirement: Local vs national query mix

The system MUST mix local and national/UK-wide templates according to `locality_stance` (see `url_intake` stance tables). National templates MUST NOT rely on a meaningless location such as filling `{location}` with only "United Kingdom" as the sole geographic signal for every query.

#### Scenario: Local-primary mix includes limited national queries

- **WHEN** stance is `local_primary` and query generation runs with a 10-query budget
- **THEN** the query set includes predominantly local/primary-location questions and at most two national/UK-wide questions

#### Scenario: Hybrid mix includes UK-wide share

- **WHEN** stance is `hybrid` and query generation runs with a 10-query budget
- **THEN** approximately three queries are national/UK-wide and the remainder are local

### Requirement: Operator overrides on URL runs

`POST /api/runs/from-url` MUST accept optional `location` and `display_name` fields. When `location` is provided, the system MUST rebuild accountant queries for that primary location and record a `location_override` usage phase. `display_name` MUST be stored on the profile snapshot for customer export labeling and matching-alias expansion but MUST NOT by itself replace `brand_name` for probes.

#### Scenario: Batch CSV location override

- **WHEN** batch export passes `location` for a firm URL
- **THEN** the from-url body includes that location and probes use the overridden geography

### Requirement: Operator URL UI

The web dashboard MUST provide a control to paste a website URL and start analysis without selecting a demo pilot. While the run is in progress, the UI MUST poll for completion using the existing run polling behaviour.

#### Scenario: Analyse from URL in dashboard

- **WHEN** the operator pastes a URL and starts analysis
- **THEN** the client calls `POST /api/runs/from-url` and polls `GET /api/runs/{id}` until the run completes or fails

