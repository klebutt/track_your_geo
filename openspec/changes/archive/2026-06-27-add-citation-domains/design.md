# Design: per-query citation domains

## Context

Probes use plain LiteLLM chat completion (`gpt-4o-mini`) with a system prompt that discourages fabricated citations. Many replies contain **no URLs**. Commercial accepts empty per-query states. Journey 2 needs **domains parsed from actual reply text**, not placeholder `seed_domains`.

**Update (May 2026):** Probes switched to OpenAI **`gpt-4o-mini-search-preview`** via Chat Completions + `web_search_options`. Citations come from `message.annotations` (`url_citation`) with text-URL parsing as fallback.

## Goals / Non-Goals

**Goals:**

- Extract normalized domains from each probe reply after the LLM call.
- Classify each domain as `brand_owned` or `third_party` using pilot `brand_domains` plus a simple brand-slug heuristic.
- Store and return citations per query; render in the dashboard with clear ownership styling.
- Ship deterministic tests without live LLM calls.

**Non-Goals:**

- OpenAI Responses API (separate surface; search-preview model suffices for MVP).
- Run-level domain leaderboards or citation-weighted scores.
- Full URL display required (domain label is enough).
- Re-enabling recommendations or changing neutral probe templates.

## Decisions

### Probe path (search model)

- Model: `TYGEO_PROBE_MODEL` default `gpt-4o-mini-search-preview`.
- LiteLLM `completion(..., web_search_options={ search_context_size, user_location })`.
- `user_location.approximate.region` set from pilot/override location string.
- Default `search_context_size`: `low` (10 probes per run — cost control).

### Extraction (deterministic)

1. **Primary:** `url_citation` entries in `message.annotations` → domain from URL.
2. **Fallback:** HTTP(S) URLs and markdown links in `response_text`.
- Normalize: lowercase host, strip `www.`, dedupe first-seen order.

### Ownership classification

1. If normalized domain is in pilot `brand_domains` → `brand_owned`.
2. Else if brand slug (alphanumeric, length ≥ 4) is substring of domain → `brand_owned`.
3. Else → `third_party`.

### Persistence

- `query_results.cited_domains` JSON column (list of `{domain, kind}`).
- SQLite: `ALTER TABLE` on startup if column missing.

### UI

- Table column **Sources (domains)** with chips; disclaimer mentions web search path.
- Remove illustrative `seed_domains` panel.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Higher cost / latency per run | `search_context_size=low`; show run cost |
| Still not consumer ChatGPT | Disclaimer |
| Heuristic mislabels domains | `brand_domains` on pilots |
| Old DB rows lack column | Migration |

## Migration Plan

1. Deploy API with search probes + column migration.
2. New runs populate `cited_domains`; re-run analysis for demos.

## Open Questions

- None for MVP.
