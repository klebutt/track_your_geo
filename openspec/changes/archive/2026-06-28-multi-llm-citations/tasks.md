# Tasks: multi-llm-citations

## Status: implemented (validation complete; Railway deploy manual)

Implement these tasks sequentially. Each adds a new provider or refactors the existing loop to support multiple models.

---

### Task 1 — Update Config ✓

**File:** `apps/api/tygeo/config.py`

Add `perplexity_api_key`, `gemini_api_key`, and `tygeo_enabled_probes` (string).
Add `enabled_probe_models` property to return a list.

---

### Task 2 — Implement Perplexity/Gemini Domain Extraction ✓

**File:** `apps/api/tygeo/citations.py`

Add `extract_domains_from_list(urls: list[str])` to handle Perplexity's citation array.
Add `extract_domains_from_gemini(response_obj: Any)` to handle Gemini's grounding metadata.

Update `build_cited_domains` to accept an optional `model_name` so it can pick the right extraction logic.

---

### Task 3 — Generic `run_geo_query` Refactor ✓

**File:** `apps/api/tygeo/llm.py`

Refactor `run_geo_query` into `run_geo_query_provider(settings, model, prompt, location)`.
- If model starts with `gpt-`: use OpenAI `web_search_options` logic.
- If model starts with `perplexity/`: pass citations array from response choice.
- If model starts with `gemini/`: pass `tools=[{"type": "google_search"}]`.

Ensure metadata (`cost_usd`, `latency_ms`, etc.) is returned consistently.

---

### Task 4 — Update `execute_run` Loop ✓

**File:** `apps/api/tygeo/analysis.py`

Refactor the query loop to iterate over `settings.enabled_probe_models`.
Calculate `visibility_rate` and `composite_score` across the total pool of model responses.

---

### Task 5 — Local Validation ✓

1. Set `TYGEO_ENABLED_PROBES=gpt-4o-mini-search-preview,perplexity/sonar-pro` (if you have keys) or use dummy responses in a test script.
2. Run a pilot and verify that multiple `query_results` rows are created per query.
3. Verify that the UI displays the model name next to each result.

---

### Task 6 — Railway Setup

1. Add `PERPLEXITY_API_KEY` and `GEMINI_API_KEY` to Railway variables.
2. Update `TYGEO_ENABLED_PROBES` to include all three models.
3. Redeploy.

---

## Validation checklist

- [x] Run analysis completes with >1 model enabled
- [x] Perplexity citations are visible in the dashboard
- [x] Gemini citations are visible in the dashboard
- [x] Total run cost reflects all models used
- [x] No regression on OpenAI search citations
