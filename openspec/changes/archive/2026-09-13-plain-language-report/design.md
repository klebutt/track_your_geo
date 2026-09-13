## Context

URL → report pipeline works locally. Operators still see a prototype dashboard centred on visibility %, composite GEO score, and per-probe tables. Sprint plan Phase 7 calls for free-result language like “AI recommends your business in 4/10 searches” plus wins/losses and competitor contrast — without GEO jargon.

Runs already store enough evidence: `visibility_rate`, `query_results` (`brand_mentioned`, `competitors_mentioned`, query text, model), and recommendations. Railway is parked; this surface is for local outreach.

**Constraint:** User wants **3 models** for outreach (including OpenAI), so “X/N” should be framed as N = distinct customer-intent questions (or probes — decide below), not “drop to 2 models”.

## Goals / Non-Goals

**Goals:**

- Plain-language report block for completed runs (especially URL intake).
- Headline recommend rate in “X of N” form.
- Short lists: questions where the firm appeared; questions where competitors appeared and the firm did not (or competitor won alongside).
- One or two sentences on biggest gaps (deterministic template from data; optional reuse of first recommendation title).
- Operator can still open technical GEO details.

**Non-Goals:**

- Public unauthenticated share links / paywall
- PDF or email delivery
- New LLM summarisation call for v1 (unless templates prove too weak)
- Changing probe count or model set
- Rewriting the scoring formula

## Decisions

1. **Derive in API as `report` summary on run payload (preferred)**  
   Add a small pure function `build_plain_report(run) -> dict` used when serialising `RunOut`, so UI and future share pages share one contract.  
   *Alternative:* UI-only — faster but duplicates logic and drifts.

2. **Define N as unique query texts (not probe rows)**  
   With 3 models, 10 questions → 30 rows. Headline “4/10” matches product language better than “12/30”. Compute: among unique queries, fraction where **any** model mentioned the brand (or average — prefer **any-model hit** for “recommended in this search”). Show optional footnote: “Across OpenAI, Perplexity, and Gemini.”

3. **Language**  
   Prefer “AI searches” / “AI assistants recommended you” over “GEO score” / “visibility gate” on the report surface. Keep composite score in the existing Insights section.

4. **Placement**  
   New dashboard section **above** Summary / Insights when a run is loaded (URL or demo), titled plainly (e.g. “Your AI recommendation report”).

## Risks / Trade-offs

- [X/N feels worse than % for sparse hits] → Still use X/N as primary; show % as secondary.
- [Unique-query aggregation hides model disagreement] → Footnote + keep per-probe table for operators.
- [Template gap copy sounds robotic] → Iterate copy after 2–3 live runs; LLM summary deferred.

## Migration Plan

- Additive API field `plain_report` (or nested under run); old clients ignore it.
- No DB migration (computed at read/serialise time from stored rows).

## Open Questions

- Exact copy for zero-visibility firms (empathetic, not doom).
- Whether to count “recommended” as brand_mentioned only, or require positive sentiment when extracted.
