# Proposal: multi-llm-citations

## What

Expand the probe engine to support multiple LLM providers concurrently:
1. **Perplexity** (`sonar-pro`) — native citations array
2. **Gemini** (`gemini-2.5-flash`) — Google Search grounding annotations
3. **OpenAI** (`gpt-4o-mini-search-preview`) — existing web search annotations

## Why

The core value prop of Track Your GEO is visibility across *all* major AI platforms. Relying on a single provider (OpenAI) gives a narrow and potentially biased signal. Diversifying the probe models increases the data quality and makes the GEO score more robust.

## Scope

**In scope:**
- Add `PERPLEXITY_API_KEY` and `GEMINI_API_KEY` to config
- Update `llm.py` to handle fan-out to multiple models
- Map provider-specific citation formats (Perplexity array, Gemini annotations) to the existing `cited_domains` structure
- Update `execute_run` to cycle through all enabled models per query
- Track which model produced each query result

**Out of scope:**
- Parallel/async fan-out (sequential is fine for prototype)
- Sentiment/position scoring (defer)
- UI changes to filter by model (results will just list the model name)

## Success criteria

1. A single run can produce results from all three providers
2. Citations from Perplexity and Gemini are correctly extracted and stored
3. Total cost and token usage aggregate correctly across all models
