# Capability: GEO probe and MVP dashboard

## Purpose

Local prototype for **Track Your GEO**: YAML pilots, batch LLM probes via LiteLLM, SQLite persistence, basic visibility and gap signals, recommendations, and run-level cost — with an honest disclaimer about API vs consumer chat.

## Requirements

### Requirement: Pilot configuration

The system MUST load pilot profiles from YAML in the configured directory. Each profile MUST include `id`, `brand_name`, `location`, `competitors`, and `queries` (templates with optional `{brand}` and `{location}` placeholders). Each profile MAY include `brand_domains` (explicit domains treated as brand-owned for citation classification). Each profile MAY include `seed_domains` for legacy compatibility; the dashboard MUST NOT present `seed_domains` as live citations from model replies.

#### Scenario: Load pilots for the UI

- **WHEN** the API receives `GET /api/pilots`
- **THEN** it returns one entry per valid YAML file discovered recursively under the configured pilot directory with id, brand, location, and query count

#### Scenario: Skip malformed pilot files

- **WHEN** a YAML file under the pilot directory fails validation
- **THEN** the API logs a warning and continues listing other pilots without failing the request

### Requirement: Simulated GEO probe

The system MUST execute each query template against every model in `TYGEO_ENABLED_PROBES` using LiteLLM and MUST persist assistant text per query on the run. Each `query_results` row MUST also persist `cited_domains` derived from provider-specific citation metadata and `model_name` identifying which probe model produced the row.

#### Scenario: Run batch probes

- **WHEN** the client calls `POST /api/runs` with a valid `pilot_id` and configured provider credentials
- **THEN** the API returns immediately with `status: running` and begins probes in a background task
- **AND** the client polls `GET /api/runs/{id}` until `status` is `completed` or `failed`

#### Scenario: Incremental probe persistence

- **WHEN** a background probe completes successfully
- **THEN** a `query_results` row is committed before the next probe starts so polling clients see growing progress

#### Scenario: Partial run on model failure

- **WHEN** an individual probe fails (e.g. provider rate limit or missing API key)
- **THEN** the failure is recorded in `usage_log` with `phase: probe_error`
- **AND** other probes continue
- **AND** the run completes with `status: completed` if at least one probe succeeded

### Requirement: Multi-provider GEO probes

GEO probes MUST fan out sequentially across the comma-separated models in `TYGEO_ENABLED_PROBES` (default: `gpt-4o-mini-search-preview`). The system MUST support:

- **OpenAI search models** — `web_search_options` with `url_citation` annotations
- **Perplexity** (`perplexity/sonar-pro`) — top-level `citations` URL array
- **Gemini** (`gemini/gemini-2.5-flash`) — `googleSearch` tool with grounding metadata

Provider API keys MUST be read from `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, and `GEMINI_API_KEY` respectively. The system MUST NOT invent citation URLs outside model output.

#### Scenario: Multi-model run metadata

- **WHEN** the client starts a run with three models enabled
- **THEN** each probe records `model_name` on its `query_results` row and the run's `model_name` lists all models used

#### Scenario: OpenAI search model configured

- **WHEN** the client starts a run with an OpenAI search model enabled
- **THEN** each OpenAI probe uses `web_search_options` and records `probe_path: web_search` in usage metadata

#### Scenario: Perplexity citations

- **WHEN** a Perplexity probe returns a `citations` array
- **THEN** cited domains are extracted from those URLs before falling back to reply text parsing

### Requirement: Web search probes for citations (OpenAI path)

OpenAI GEO probes MUST use a search-capable model (default `gpt-4o-mini-search-preview`) with `web_search_options` so replies include provider `url_citation` annotations.

### Requirement: Citation domain extraction

After each probe completes, the system MUST extract domains from provider-grounded metadata when present:

- OpenAI: `url_citation` annotations
- Perplexity: `citations` URL list (and `search_results` fallback)
- Gemini: grounding chunks / annotations mapped by LiteLLM

The system MAY supplement from HTTP(S) URLs or markdown links in `response_text`. The system MUST NOT invent domains not present in annotations, citation arrays, or text.

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

The web dashboard MUST show extracted domains and `model_name` for each query result. An empty citation list MUST be shown explicitly (e.g. “No domains cited”). The dashboard MUST distinguish brand-owned and third-party domains visually.

#### Scenario: Per-query sources in results table

- **WHEN** a user views query-level results after a completed run
- **THEN** each row shows the domains cited in that query’s reply, or an explicit empty state

#### Scenario: Citations disclaimer

- **WHEN** citation domains are shown
- **THEN** the UI includes copy that domains are parsed from this API path’s reply text and are not guaranteed to match consumer chat products

### Requirement: Consumer parity disclaimer

The product MUST communicate that API completions are not identical to consumer chat experiences (tools, browsing, regional routing may differ).

#### Scenario: Disclaimer in dashboard

- **WHEN** a user opens the web UI
- **THEN** a visible disclaimer explains that results are directional for this model path and not guaranteed parity with any consumer product

### Requirement: Visibility and competitor signals

The system MUST compute visibility rate as the fraction of stored probe responses (across all enabled models) where the brand name appears as a case-insensitive substring in the assistant text. The system MUST store per-competitor boolean mention flags for each query.

#### Scenario: Mark brand presence

- **WHEN** a stored assistant text contains the pilot brand substring
- **THEN** the corresponding `query_results` row records `brand_mentioned` as true, otherwise false

### Requirement: Recommendations

After probes complete, the system MUST call the LLM for a JSON array of recommendations and MUST persist title, detail, impact, and category linked to the run.

#### Scenario: Persist structured actions

- **WHEN** a run completes probing
- **THEN** the API stores at least one recommendation row when the model returns parsable JSON items

### Requirement: Cost observability

The system MUST aggregate per-call token counts and LiteLLM-reported costs for each run and MUST expose totals on the run payload. LiteLLM MAY return cost as a float or a breakdown dict; the system MUST normalize to a single USD float per probe.

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
