## MODIFIED Requirements

### Requirement: Profile inference from website URL

The system MUST attempt to fetch the URL (with timeout and response size limits) and MUST use an LLM structured extraction step to populate profile fields from page text when fetch succeeds. When fetch fails or yields insufficient text, the system MUST attempt a search-grounded or LLM enrichment fallback using the URL/domain so that a best-effort profile can still be produced.

After extract (and any thin-page brand/location enrich), if `competitors` is empty or `aliases` is empty (after deterministic alias generation), the system MUST run an enrichment step to populate competitor and/or alias lists when reasonably possible for the vertical and location. Enrichment MUST NOT be skipped solely because `brand_name` and `location` were already present from the homepage extract.

When the inferred location string names multiple places (e.g. a comma-separated office list), the system MUST derive a single primary location for accountant query template fill. The profile snapshot MUST still expose enough location detail for operator review (primary location required; fuller raw location MAY be retained when it differs).

For vertical `accountants`, the system MUST infer a `locality_stance` of `local_only`, `local_primary`, `hybrid`, `remote_primary`, or `unclear` from site signals during extract and/or enrich (cheap LLM JSON fields). Cloud accounting software alone MUST NOT force `hybrid`; UK-wide or remote-client claims MAY. The profile snapshot MUST include `locality_stance`. Competitor enrichment MUST prefer local/regional rivals when stance is `local_only` or `local_primary`.

Inference token/cost MUST be recorded in `usage_log` with distinct phases for fetch/extract/enrich/query generation as applicable.

#### Scenario: Successful HTML extract

- **WHEN** the homepage HTML is fetched successfully
- **THEN** the system extracts at least `brand_name` and `location` (location MAY be empty if truly unknown) and records extract cost/usage when an LLM is called

#### Scenario: Fetch failure fallback

- **WHEN** the HTTP fetch fails (timeout, block, or empty body)
- **THEN** the system still attempts enrichment from the URL/domain
- **AND** proceeds to probes if a `brand_name` can be inferred
- **AND** records the failure in `usage_log` without aborting the whole run unless no brand name can be inferred

#### Scenario: Competitor enrich after successful extract

- **WHEN** homepage extract yields a brand name and location but an empty competitors list
- **THEN** the system runs an enrichment step that attempts to populate competitors
- **AND** records the enrich call in `usage_log`
- **AND** the profile snapshot used for the run includes any competitors returned (capped)

#### Scenario: Multi-office location normalised for queries

- **WHEN** the inferred location string contains multiple comma-separated places
- **THEN** query templates are filled with a single primary location
- **AND** the profile snapshot retains enough information for an operator to see the broader location context when it differed from the primary

#### Scenario: Locality stance persisted

- **WHEN** URL intake completes profile inference for accountants
- **THEN** the profile snapshot includes a `locality_stance` value from the allowed taxonomy

### Requirement: Accountant query generation

For vertical `accountants`, the system MUST build approximately 8–15 brand-neutral customer-intent queries from template banks combined with inferred location, services, and `locality_stance`. Queries MUST NOT include the target brand name in the prompt text. Other verticals MAY be rejected with `4xx`.

The system MUST mix **local** templates (using primary location) and **national/UK-wide** templates according to stance: `local_only` all local; `local_primary` mostly local with up to two national; `hybrid` about 30% national (~3 of 10); `remote_primary` mostly national; `unclear` treated as `local_primary`. National templates MUST NOT rely on a meaningless location such as filling `{location}` with only "United Kingdom" as the sole geographic signal for every query.

#### Scenario: Generate accountant queries

- **WHEN** a URL run uses vertical `accountants` and a location is available
- **THEN** the inferred profile includes multiple queries that mention the location or service themes without naming the brand

#### Scenario: Unsupported vertical

- **WHEN** the client requests a vertical other than `accountants`
- **THEN** the API responds with `4xx` explaining only `accountants` is supported in this version

#### Scenario: Local-primary mix includes limited national queries

- **WHEN** stance is `local_primary` and query generation runs with a 10-query budget
- **THEN** the query set includes predominantly local/primary-location questions and at most two national/UK-wide questions

#### Scenario: Hybrid mix includes UK-wide share

- **WHEN** stance is `hybrid` and query generation runs with a 10-query budget
- **THEN** approximately three queries are national/UK-wide and the remainder are local
