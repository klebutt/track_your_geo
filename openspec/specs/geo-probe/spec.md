# Capability: GEO probe and MVP dashboard

## Purpose

Local prototype for **Track Your GEO**: YAML pilots, batch LLM probes via LiteLLM, SQLite persistence, basic visibility and gap signals, recommendations, and run-level cost — with an honest disclaimer about API vs consumer chat.

## Requirements

### Requirement: Pilot configuration

The system MUST load pilot profiles from YAML in the configured directory. Each profile MUST include `id`, `brand_name`, `location`, `competitors`, and `queries` (templates with optional `{brand}` and `{location}` placeholders). Each profile MAY include `seed_domains` shown only as illustrative when citations are missing.

#### Scenario: Load pilots for the UI

- **WHEN** the API receives `GET /api/pilots`
- **THEN** it returns one entry per valid YAML file with id, brand, location, and query count

### Requirement: Simulated GEO probe

The system MUST execute each query template against the configured model using LiteLLM and MUST persist assistant text per query on the run.

#### Scenario: Run batch probes

- **WHEN** the client calls `POST /api/runs` with a valid `pilot_id` and configured provider credentials
- **THEN** the API creates a run that includes one stored result row per pilot query with model output text

### Requirement: Consumer parity disclaimer

The product MUST communicate that API completions are not identical to consumer chat experiences (tools, browsing, regional routing may differ).

#### Scenario: Disclaimer in dashboard

- **WHEN** a user opens the web UI
- **THEN** a visible disclaimer explains that results are directional for this model path and not guaranteed parity with any consumer product

### Requirement: Visibility and competitor signals

The system MUST compute visibility rate as the fraction of queries where the brand name appears as a case-insensitive substring in the assistant text. The system MUST store per-competitor boolean mention flags for each query.

#### Scenario: Mark brand presence

- **WHEN** a stored assistant text contains the pilot brand substring
- **THEN** the corresponding `query_results` row records `brand_mentioned` as true, otherwise false

### Requirement: Recommendations

After probes complete, the system MUST call the LLM for a JSON array of recommendations and MUST persist title, detail, impact, and category linked to the run.

#### Scenario: Persist structured actions

- **WHEN** a run completes probing
- **THEN** the API stores at least one recommendation row when the model returns parsable JSON items

### Requirement: Cost observability

The system MUST aggregate per-call token counts and LiteLLM-reported costs for each run and MUST expose totals on the run payload.

#### Scenario: Show run cost

- **WHEN** the client fetches `GET /api/runs/{id}` after a successful run
- **THEN** the response includes `total_cost_usd` and token totals derived from LiteLLM usage metadata

### Requirement: Persistence

The system MUST use SQLite to store runs, per-query rows, and recommendations so results can be retrieved later without re-invoking models.

#### Scenario: Fetch historical run

- **WHEN** the client calls `GET /api/runs/{id}` for an existing id
- **THEN** the API returns stored query rows and recommendations without re-running probes

### Requirement: Automated evaluation hooks

The repository MUST ship tests for deterministic mention logic and at least one DeepEval metric test that does not require live LLM probes.

#### Scenario: CI-safe regression tests

- **WHEN** a developer runs `pytest eval`
- **THEN** substring-based DeepEval metrics and pure unit tests execute without network calls
