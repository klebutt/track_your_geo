# GEO scoring: how close are we to “real” ChatGPT search?

The prototype measures **simulated** visibility: neutral user-style questions, answers from **configured LLM APIs** (via LiteLLM, multi-model by default), a **case-insensitive substring** gate for brand visibility, and — when the brand appears — a **structured extraction** call (`gpt-4o-mini`, JSON mode) for sentiment, mention position, and relevance. The run **composite score** blends visibility, position, sentiment, and citation volume (see [apps/api/docs/geo-scoring-formula.md](../apps/api/docs/geo-scoring-formula.md)).

That stack is useful for **trends and comparisons** inside the product, but it is **not** the same as what any given user sees in **consumer ChatGPT** (or other assistants) when they use **search-like** behaviour.

This note explains the gap and practical ways to move toward a score that **tracks** real-world visibility more closely.

---

## What still diverges from consumer ChatGPT-style search

| Factor | Typical API prototype (this repo) | Consumer ChatGPT-style search |
|--------|-----------------------------------|-------------------------------|
| **Model & stack** | Configured probe models (`TYGEO_ENABLED_PROBES`) | May differ by tier, rollout, and internal routing |
| **Web / search tools** | Usually **no live browse** | Often **search + browse**, snippets, links, recency |
| **Geo** | Region implied mainly in prompt text | Account, IP, locale, and product defaults |
| **Queries** | Curated bank of probes | Long tail of real phrasing, follow-ups, refinements |
| **Measurement** | Substring visibility gate + LLM extraction for sentiment/position on visible rows | Lists, cards, citations; entities may appear without the exact brand string |

Until you measure **on the consumer surface** or build a **calibrated proxy**, a single percentage should be read as an **index**, not parity with “what ChatGPT showed me yesterday.”

---

## Ways to get closer (roughly in order of fidelity)

### 1. Measure on the consumer path (strongest anchor, hardest operationally)

Run the same **neutral** questions through the **actual product** you care about (with appropriate consent, tooling, and respect for **terms of use**), in the **target market** (e.g. UK), and for the **subscription tier** that matters (e.g. Plus).

- Captures browsing, citations, layout, and routing.
- Does not scale cheaply; UI and product behaviour change often.

This is the only approach that is **by definition** “what users see” on that product.

### 2. Use vendor search- or browse-grounded APIs where allowed

If the provider exposes **search-grounded** or **web-enabled** completions you are allowed to use in production, run probes through that path instead of plain chat completion.

- Still not identical to the consumer app, but restores **freshness and retrieval**, which strongly affect who gets mentioned.

### 3. Enrich probes from real intent

- Derive or sample **how people actually ask** (support themes, sales calls, SEO/PAA-style queries, anonymised search logs).
- Add **variants** per intent (short vs long, “best” vs “cheap” vs “near X”).

More probes reduce **variance**; realistic phrasing reduces **systematic bias** vs a hand-written list.

### 4. Move beyond substring match for “visible”

**Shipped (2026-06-28):** When the substring gate finds the brand, a cheap **structured LLM extraction** call records sentiment (`positive` / `neutral` / `negative`), mention position (`first_mentioned` / `secondary`), and relevance. These feed the weighted composite score alongside citations. Extraction is skipped when the brand is not visible (~$0.001 per visible row).

Remaining gaps vs user perception:

- Substring gate can still false-positive (e.g. partial name matches) or miss entities named differently.
- The extraction judge should be **calibrated** on a human-labelled sample so drift is visible over time.
- **Entity / canonical ID** resolution when you have a stable knowledge base.

### 5. Report a small bundle, not one headline number

Closer to how users experience search:

- Rate of **unprompted** mention in **top suggestions** (when you can define “top” structurally).
- **Who else** appears (competitive context).
- **By intent cluster** (e.g. theatre dinner vs Indian vs City lunch).

A single scalar hides the behaviour users actually feel.

### 6. Calibration layer

Maintain a **small, stable panel** of questions evaluated periodically on ChatGPT (or by humans) and **fit** your API-based metrics so they **track** the panel over time (e.g. weighted blend, or simple regression).

Ship the score as something like: **“Visibility index v3, calibrated to panel Feb 2026”** — honest about what moves when the panel or API changes.

---

## What we should not claim

A **multi-model API** run with **search-grounded probes**, **substring visibility gate**, and **LLM extraction** for sentiment/position is **not** “the ChatGPT score.” It can still be a **useful internal and longitudinal signal** if labelled clearly (e.g. API visibility index under stated assumptions).

---

## Smallest useful next steps

Pick one direction and make it explicit in product copy and specs:

1. **Calibration** — Small recurring panel on the consumer product vs current index; document drift.
2. **Search-enabled API path** — When licensing and access allow, add a second “grounded” channel and report both scores.
3. **Extraction judge calibration** — Human-label a fixed sample of probe replies; track extraction accuracy over prompt/model changes.

---

## Related code in this repo

- Probe text: `apps/api/pilots/` YAML templates (brand-neutral queries only).
- Visibility gate: `apps/api/tygeo/analysis.py` (`_mentions`, `analyze_response`) — case-insensitive substring.
- Structured extraction: `apps/api/tygeo/llm.py` (`extract_mention_details`) — `gpt-4o-mini`, JSON mode; only when substring gate passes.
- Composite score: `apps/api/tygeo/analysis.py` (`query_geo_score`, `aggregate_composite_score`); formula in [apps/api/docs/geo-scoring-formula.md](../apps/api/docs/geo-scoring-formula.md).
- Execution: `apps/api/tygeo/analysis.py` (`execute_run`, background `finish_run_probes`), multi-model LLM in `apps/api/tygeo/llm.py`.
- Runs are **async**: UI polls `GET /api/runs/{id}`; per-model failures can yield partial results (common for Gemini free tier).
- **History:** selecting a brand loads the latest completed run via `GET /api/runs?pilot_id=…`; a trend chart plots visibility % over past runs (still not consumer-chat parity).
- **Dashboard:** query table shows Sentiment and Position columns per probe row (prod verified 2026-06-28).
