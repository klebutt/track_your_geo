# Proposal: Brand match precision and run rescore (retroactive)

**Status:** Retroactive documentation — behaviour shipped without an OpenSpec change in October 2026.

## Why

PRs [#11](https://github.com/klebutt/track_your_geo/pull/11), [#12](https://github.com/klebutt/track_your_geo/pull/12), and [#13](https://github.com/klebutt/track_your_geo/pull/13) replaced naive case-insensitive substring visibility with normalized token matching, added directory and generic-"town accountants" guards, wired `display_name` into alias expansion, and introduced `POST /api/runs/{id}/rescore` plus batch regenerate integration. Canonical specs still described September substring behaviour.

## What changed (as implemented)

- `tygeo/brand_match.py` — URL stripping, normalization, token-sequence match, short-alias rules, `build_matching_aliases`, directory prefix guard, generic accountants exclusion.
- `tygeo/analysis.analyze_response` — uses expanded aliases and `mentions_phrase` for competitors.
- `tygeo/rescore.py` + `POST /api/runs/{run_id}/rescore` — recompute rows and aggregates without probe LLM calls; drop stale recommendations.
- `scripts/batch_export.py` — rescore on `--regenerate` by default (`--no-rescore` to skip).

## Capabilities

- Modified: `geo-probe` (visibility/competitor matching, rescore API).

## Uncertainty

- PR #13 also adjusted customer gap copy thresholds in `plain_report.py`; those are captured under `plain-language-report` (September + October archives), not duplicated here.
