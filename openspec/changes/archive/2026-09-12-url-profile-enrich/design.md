## Context

URL intake (`infer_pilot_from_url`) currently runs `profile_enrich` only when brand is missing, location is missing, or page text is thin (`need_enrich`). Successful scrapes that already yield name + location skip enrich. Homepage extract asks for competitors “if clearly mentioned” — firm sites almost never list rivals — so `competitors` stays `[]`. Alias generation only strips Ltd/LLP-style suffixes from the brand string, so names like “Bennett Brooks” get no aliases.

Location is passed straight into accountant query templates. Multi-office extracts (e.g. “Bristol, Bath, Yeovil, Taunton, London, UK”) make every query noisy and less local.

Outreach for ~50 accountants will run locally (Railway parked). Inference quality matters more than prod deploy right now.

## Goals / Non-Goals

**Goals:**

- Populate competitors (and useful aliases) after extract when those lists are empty, via a dedicated enrich LLM call.
- Choose a single primary location for query template fill while preserving richer location text on the profile snapshot when available.
- Keep cost visible (`usage_log` phase `profile_enrich`) and tests deterministic (mocked LLM).

**Non-Goals:**

- Plain-language customer report UI
- Operator batch URL queue
- Changing probe model set or Railway config
- Perfect NER / entity linking
- Requiring accountant confirmation of competitors

## Decisions

1. **Enrich trigger = gap-fill, not scrape failure only**  
   After extract (or thin-page enrich for brand/location), if `competitors` is empty OR `aliases` is empty (after `generate_aliases`), call `enrich_profile_from_url` and merge non-empty lists. Prompt prefers local/regional rivals, then nationals; forbids inventing fake firms/addresses; excludes the target brand; asks for 3–8 names. Self-matches are filtered in code.  
   *Alternative considered:* Always enrich — rejected as wasting a call when extract already returned competitors.  
   *Alternative considered:* Infer competitors only from probe answer text post-run — deferred; we need competitors *before* probes for substring competitor checks.

2. **Primary location for queries**  
   Add a small normalisation step: if location contains multiple comma-separated places, pick one primary (prefer first city-like token / first segment before a long list; fall back to first segment). Store `location` as primary for probes/templates; optionally keep `location_raw` or full string in snapshot.  
   *Alternative considered:* LLM “pick primary city” every time — optional later if heuristics fail; start with deterministic split to avoid extra cost.

3. **Alias generation**  
   Keep suffix stripping; merge enrich-provided aliases; do not invent unrelated trading names without enrich signal.

4. **API**  
   No new endpoints; behaviour change inside existing from-url pipeline.

## Risks / Trade-offs

- [Hallucinated competitors] → Mitigation: prompt “plausible local/national rivals for this vertical+location”; cap list size (existing `[:8]`); operator spot-checks snapshots during outreach.
- [Extra ~$0.001–0.01 per URL] → Acceptable vs ~$0.50 run; log phase cost.
- [Wrong primary city] → Mitigation: prefer first segment; add LLM pick only if smoke shows frequent misses.
- [Enrich still returns empty] → Mitigation: tests + prompt tighten; fail soft (empty list) without aborting run.

## Migration Plan

- Local-only: pull change, re-run 1–2 prior smoke URLs, compare `profile_snapshot`.
- No DB migration; new runs only.
- Rollback: revert enrich-gate change; old behaviour returns.

## Open Questions

- Whether to store `location_raw` separately vs overwrite `location` with primary only (recommend: primary in `location`, raw in snapshot under `location_raw` if different).
