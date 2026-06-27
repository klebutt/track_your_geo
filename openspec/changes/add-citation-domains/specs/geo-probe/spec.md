# Delta spec: `geo-probe` (change `add-citation-domains`)

Baseline capability lives in [`../../../specs/geo-probe/spec.md`](../../../specs/geo-probe/spec.md).

## ADDED Requirements

### Requirement: Citation domain extraction

After each probe completes, the system MUST parse the assistant `response_text` and extract a deduplicated ordered list of internet domain names found in HTTP(S) URLs or markdown link targets. The system MUST NOT invent domains not present in the text.

#### Scenario: Extract domains from URLs in reply

- **WHEN** the assistant text contains `https://www.timeout.com/london/restaurants`
- **THEN** the stored citation list for that query includes domain `timeout.com`

#### Scenario: No domains in reply

- **WHEN** the assistant text contains no parseable URLs or markdown links with hosts
- **THEN** the stored citation list for that query is empty

### Requirement: Brand-owned vs third-party classification

Each extracted domain MUST be classified as `brand_owned` or `third_party`. The system MUST use pilot-configured `brand_domains` when provided. When `brand_domains` is empty, the system MAY classify a domain as `brand_owned` only when the normalized brand name slug (alphanumeric, length ≥ 4) appears in the domain label.

#### Scenario: Explicit brand domain

- **WHEN** the pilot lists `brand_domains: ["dishoom.com"]` and the reply cites `https://dishoom.com/menu`
- **THEN** the citation entry for `dishoom.com` has `kind` `brand_owned`

#### Scenario: Third-party domain

- **WHEN** the reply cites `https://tripadvisor.com/...` and that domain is not in `brand_domains` and does not match the brand slug heuristic
- **THEN** the citation entry has `kind` `third_party`

### Requirement: Per-query citation display

The web dashboard MUST show extracted domains for each query result. An empty citation list MUST be shown explicitly (e.g. “No domains cited”). The dashboard MUST distinguish brand-owned and third-party domains visually.

#### Scenario: Per-query sources in results table

- **WHEN** a user views query-level results after a completed run
- **THEN** each row shows the domains cited in that query’s reply, or an explicit empty state

#### Scenario: Citations disclaimer

- **WHEN** citation domains are shown
- **THEN** the UI includes copy that domains are parsed from this API path’s reply text and are not guaranteed to match consumer chat products

## MODIFIED Requirements

### Requirement: Pilot configuration

The system MUST load pilot profiles from YAML in the configured directory. Each profile MUST include `id`, `brand_name`, `location`, `competitors`, and `queries` (templates with optional `{brand}` and `{location}` placeholders). Each profile MAY include `brand_domains` (explicit domains treated as brand-owned for citation classification). Each profile MAY include `seed_domains` for legacy compatibility; the dashboard MUST NOT present `seed_domains` as live citations from model replies.

#### Scenario: Load pilots for the UI

- **WHEN** the API receives `GET /api/pilots`
- **THEN** it returns one entry per valid pilot with id, brand, location, and query count

#### Scenario: Pilot detail includes brand domains

- **WHEN** the API receives `GET /api/pilots/{id}`
- **THEN** the response includes `brand_domains` when configured on the pilot

### Requirement: Simulated GEO probe

The system MUST execute each query template against the configured model using LiteLLM and MUST persist assistant text per query on the run. Each `query_results` row MUST also persist `cited_domains` derived from that assistant text.

#### Scenario: Run batch probes

- **WHEN** the client calls `POST /api/runs` with a valid `pilot_id` and configured provider credentials
- **THEN** the API creates a run that includes one stored result row per pilot query with model output text and `cited_domains`
