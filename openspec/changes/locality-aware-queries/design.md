## Context

Vault `accountant-prospects` tags locality from site signals. Product must infer the same taxonomy on URL intake. Locked 2026-09-13: local_primary may include 1–2 national niche queries; hybrid ~30% UK-wide (3/10); stance via cheap LLM fields on extract/enrich.

## Goals / Non-Goals

**Goals:** Stance on snapshot; mixed query banks; locality-aware competitor prompt; report geography footnote.

**Non-Goals:** Importing prospect list; operator tagging UI; changing probe model count.

## Decisions

1. **Stance values:** `local_only | local_primary | hybrid | remote_primary | unclear` (+ optional `online_remote`: `yes|partial|no|unclear`). Default unclear → local_primary mix.
2. **Mix table (N=10):** local_only 10+0; local_primary 8+2; hybrid 7+3; remote_primary 3+7.
3. **Templates:** YAML with `local` and `national` lists; national templates must not require a meaningful town (use UK / online / remote phrasing).
4. **Competitors:** enrich prompt branches on stance — local_primary/local_only emphasise same-area independents first.
5. **Report:** `geography_note` on `plain_report` from snapshot stance.

## Risks / Trade-offs

- [Misclassified stance] → snapshot + evidence; spot-check Top 10 vs vault tags.
- [Sparse local AI answers for tiny towns] → keep “near {location}” phrasing; county fallback later if needed.

## Open Questions

- None — rules locked 2026-09-13.
