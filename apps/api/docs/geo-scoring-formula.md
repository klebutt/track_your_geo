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

When the brand is not visible (substring gate), extraction is skipped and defaults apply: `sentiment=neutral`, `mention_position=not_mentioned`, `relevance_score=0.0`.
