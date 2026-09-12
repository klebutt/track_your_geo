# Worklog — 2026-09-12 (url-profile-enrich)

## Shipped

OpenSpec **url-profile-enrich** implemented:

- Gap-fill enrich when competitors or aliases empty after homepage extract (even if brand+location present)
- Tightened enrich prompt: local/regional rivals first, then nationals; no fake firms/addresses; exclude brand; 3–8 names
- Code filters self-matches out of competitor list
- `primary_location()` for multi-office strings; queries use primary; `location_raw` on snapshot when different
- Tests: **61 passed**

## Live infer smoke (Bennett Brooks)

- URL: `https://www.bennettbrooks.co.uk/` (infer only, no probes)
- Phases: `url_fetch` → `profile_extract` → `profile_enrich` → `query_gen`
- Location: `Northwich, UK`
- Competitors: Harts Accountants, DTE Business Advisers, Baker Tilly, MHA Moore and Smalley, Saffery Champness, RSM UK, Grant Thornton
- Aliases: still `[]` (enrich did not invent trading names; no Ltd suffix to strip)
- Enrich cost: ~$0.0002

## Next

- Archive `url-profile-enrich` when satisfied
- Plain-language report packaging for outreach
- Railway/prod remain parked
