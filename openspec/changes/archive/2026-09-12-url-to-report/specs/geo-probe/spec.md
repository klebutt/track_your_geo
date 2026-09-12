## MODIFIED Requirements

### Requirement: Pilot configuration

The system MUST load pilot profiles from YAML in the configured directory. Each profile MUST include `id`, `brand_name`, `location`, `competitors`, and `queries` (templates with optional `{brand}` and `{location}` placeholders). Each profile MAY include `url`, `aliases` (alternative name strings used for visibility matching), `industry`, `services`, `brand_domains` (explicit domains treated as brand-owned for citation classification), and `seed_domains` for legacy compatibility; the dashboard MUST NOT present `seed_domains` as live citations from model replies. Inferred profiles created via URL intake MUST satisfy the same required fields before probes execute.

#### Scenario: Load pilots for the UI

- **WHEN** the API receives `GET /api/pilots`
- **THEN** it returns one entry per valid YAML file discovered recursively under the configured pilot directory with id, brand, location, and query count

#### Scenario: Skip malformed pilot files

- **WHEN** a YAML file under the pilot directory fails validation
- **THEN** the API logs a warning and continues listing other pilots without failing the request

#### Scenario: Profile with aliases

- **WHEN** a pilot YAML includes an `aliases` list
- **THEN** the profile loads successfully and aliases are available to visibility matching

### Requirement: Visibility and competitor signals

The system MUST compute visibility rate as the fraction of stored probe responses (across all enabled models) where the brand name **or any configured alias** appears as a case-insensitive substring in the assistant text. The system MUST store per-competitor boolean mention flags for each query.

#### Scenario: Brand substring hit

- **WHEN** a stored assistant text contains the pilot brand substring
- **THEN** the corresponding `query_results` row records `brand_mentioned` as true, otherwise false

#### Scenario: Alias substring hit

- **WHEN** a stored assistant text does not contain `brand_name` but does contain a configured alias as a case-insensitive substring
- **THEN** the corresponding `query_results` row records `brand_mentioned` as true

## ADDED Requirements

### Requirement: Runs from inferred URL profiles

The system MUST allow analysis runs that use an inferred `PilotProfile` produced from URL intake, not only a pre-existing YAML `pilot_id`. Such runs MUST persist enough profile snapshot data on the run (brand name, location, aliases, competitors, queries, source URL) for later inspection and re-test. Existing `POST /api/runs` with `pilot_id` MUST continue to work unchanged.

#### Scenario: URL-inferred run persists profile snapshot

- **WHEN** a run started from a URL completes
- **THEN** the run record (or associated metadata) includes the inferred brand name, source URL, aliases, competitors, and query list used
