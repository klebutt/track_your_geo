# GEO composite score formula

Per-query GEO score (0.0–1.0) is a weighted blend of four components:

| Component | Weight | Scoring |
|-----------|--------|---------|
| **Visibility** | 40% | 1.0 if the brand substring match succeeded; 0.0 otherwise |
| **Position** | 30% | `first_mentioned` = 1.0, `secondary` = 0.5, `not_mentioned` = 0.0 |
| **Sentiment** | 20% | `positive` = 1.0, `neutral` = 0.5, `negative` = 0.0 |
| **Citation volume** | 10% | Linear scale: `min(1.0, citation_count / 5)` |

Run-level **composite score** (0–100) is the arithmetic mean of per-query scores × 100, rounded to two decimals.

Implementation: `tygeo.analysis` (`query_geo_score`, `composite_score`).

The web dashboard **ScoreBreakdown** component (`apps/web/src/ScoreBreakdown.tsx`) shows the same weights as progress bars and point contributions for the loaded run.

When the brand is not visible (substring gate), extraction is skipped and defaults apply: `sentiment=neutral`, `mention_position=not_mentioned`, `relevance_score=0.0`.

## Recommendations input

After probes complete, `execute_run` aggregates run-level signals for the recommendations LLM call:

| Signal | Source |
|--------|--------|
| Sentiment summary | Count of positive / neutral / negative among visible rows |
| Average position | Mean position score (first = 1.0, secondary = 0.5) on visible rows |
| Citation gaps | Third-party domains cited alongside competitors but not the brand |
| Weak queries | Probes where the brand was missing or not first-mentioned |
| Competitor wins | Competitors mentioned when the brand was missing or not first |

The call returns 3–5 items with `title`, `detail`, `impact` (high/medium/low), and `category` (`website`, `third_party`, `pr_comms`, `technical`, `other`). Cost is ~$0.005/run. Failures are logged as `recommendations_error` in `usage_log` without failing the run.

Implementation: `tygeo.llm.run_recommendations`, persisted via `tygeo.models.Recommendation`.
