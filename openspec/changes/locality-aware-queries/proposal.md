## Why

Most WTP accountant prospects are `local_primary` / `local_only`. Today's query bank always fills `{location}`, so weak or UK-wide locations produce irrelevant national probes and undercut local acquisition conversations. We need locality-aware query mix and competitor enrich before burning Top 10 / ~50 runs.

## What Changes

- Infer `locality_stance` (and optional `online_remote`) via cheap LLM during URL profile extract/enrich, using vault taxonomy.
- Split accountant templates into local vs UK-wide/national banks; mix by stance (locked rules below).
- Prefer local/regional competitors for local stances; allow more nationals for hybrid/remote.
- Persist stance on profile snapshot; plain-report footnote describing geographic mix.
- **Locked mix (10 queries):** `local_only` 10/0; `local_primary` 8/2; `hybrid` 7/3; `remote_primary` 3/7; `unclear` → treat as `local_primary`.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `url-intake`: locality stance inference; locality-aware query generation and competitor enrich.
- `plain-language-report`: geographic mix footnote on the recommend report.

## Impact

- `apps/api/tygeo/url_intake.py`, templates under `pilots/templates/`, `plain_report.py`, `pilots.py`, eval tests, dashboard footnote if API exposes note
- Cost: negligible (stance fields on existing extract/enrich JSON)
- Prospect list stays vault-only
