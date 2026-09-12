## MODIFIED Requirements

### Requirement: Profile inference from website URL

The system MUST attempt to fetch the URL (with timeout and response size limits) and MUST use an LLM structured extraction step to populate profile fields from page text when fetch succeeds. When fetch fails or yields insufficient text, the system MUST attempt a search-grounded or LLM enrichment fallback using the URL/domain so that a best-effort profile can still be produced.

After extract (and any thin-page brand/location enrich), if `competitors` is empty or `aliases` is empty (after deterministic alias generation), the system MUST run an enrichment step to populate competitor and/or alias lists when reasonably possible for the vertical and location. Enrichment MUST NOT be skipped solely because `brand_name` and `location` were already present from the homepage extract.

When the inferred location string names multiple places (e.g. a comma-separated office list), the system MUST derive a single primary location for accountant query template fill. The profile snapshot MUST still expose enough location detail for operator review (primary location required; fuller raw location MAY be retained when it differs).

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
