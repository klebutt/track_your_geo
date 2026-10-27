# Delta spec: `geo-probe` (retroactive change `brand-match-precision`)

Baseline before this change described case-insensitive substring visibility. Current canonical spec: [`../../../specs/geo-probe/spec.md`](../../../specs/geo-probe/spec.md).

## MODIFIED Requirements

### Requirement: Visibility and competitor signals

The system MUST compute visibility rate using normalized phrase matching (`tygeo.brand_match`) rather than case-insensitive substrings, including URL stripping, token-sequence match, short-alias rules, display-name alias expansion, generic "{Town} Accountants" exclusion, and directory-prefix competitor guards. Competitors MUST use the same `mentions_phrase` rules.

#### Scenario: Brand phrase hit after normalization

- **WHEN** a stored assistant text contains a normalized token-sequence match for `brand_name` or an expanded alias
- **THEN** the corresponding `query_results` row records `brand_mentioned` as true

## ADDED Requirements

### Requirement: Run rescore from stored replies

The API MUST expose `POST /api/runs/{run_id}/rescore` for completed runs to recompute mention flags and aggregates from stored `response_text` without probe LLM calls, and MUST delete stale recommendations.

#### Scenario: Rescore updates visibility

- **WHEN** rescore runs after improved matching rules and stored text now matches the brand
- **THEN** run-level `visibility_rate` reflects the new mention flags
