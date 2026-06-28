# Design: multi-llm-citations

## Model Configuration

We will use LiteLLM to unify the calls. Update `config.py` to include the new keys and a list of enabled probe models.

```python
# config.py
perplexity_api_key: str | None = None
gemini_api_key: str | None = None

# New setting to define which models to run
# Default to just OpenAI for backward compatibility
tygeo_enabled_probes: str = "gpt-4o-mini-search-preview" 

@property
def enabled_probe_models(self) -> list[str]:
    return [m.strip() for m in self.tygeo_enabled_probes.split(",") if m.strip()]
```

On Railway, set `TYGEO_ENABLED_PROBES=gpt-4o-mini-search-preview,perplexity/sonar-pro,gemini/gemini-2.5-flash`.

---

## Unified Citation Extraction

Update `citations.py` to handle Perplexity and Gemini formats.

### 1. Perplexity format
Perplexity returns a top-level `citations` array of URLs.

```python
def extract_domains_from_perplexity(citations: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for url in citations:
        domain = _domain_from_url(url)
        if domain and domain not in seen:
            seen.add(domain)
            ordered.append(domain)
    return ordered
```

### 2. Gemini format
Gemini grounding returns `grounding_metadata` with `search_entry_point` and `grounding_chunks`.

```python
def extract_domains_from_gemini(response: Any) -> list[str]:
    # LiteLLM maps Gemini grounding to choice.message.annotations in some versions,
    # or keeps it in response.grounding_metadata.
    # We will check both.
    pass
```

---

## Model Fan-out

Update `run_geo_query` in `llm.py` to be a generic dispatcher.

```python
def run_geo_query_multi(
    settings: Settings,
    model: str,
    user_prompt: str,
    location: str | None = None
) -> tuple[str, dict[str, Any], list[dict]]:
    # 1. Set API keys
    # 2. Call LiteLLM with provider-specific extras (tools for gemini, web_search for openai)
    # 3. Extract text and citations
    # 4. Return unified result
```

Update `execute_run` in `analysis.py`:

```python
for q_template in pilot.queries:
    for model in settings.enabled_probe_models:
        # Run query per model
        # Store separate QueryResult rows
```

---

## Database Impact

The `query_results` table already has a `model_name` column. We will now store multiple rows for the same `query_text` within one `run_id`, distinguished by `model_name`.

The `visibility_rate` calculation will now be an average across all models.

---

## Integration Details (LiteLLM)

- **Perplexity:** `model="perplexity/sonar-pro"`, `api_key=settings.perplexity_api_key`
- **Gemini:** `model="gemini/gemini-2.5-flash"`, `api_key=settings.gemini_api_key`, `tools=[{"type": "google_search"}]`
- **OpenAI:** Existing `web_search_options` path.
