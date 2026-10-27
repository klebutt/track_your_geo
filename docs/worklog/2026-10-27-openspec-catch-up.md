# OpenSpec catch-up (PRs #1–#16)

**Scope:** Docs and specs only — no product code changes.

## Done

- Merged September archive deltas into `openspec/specs/`:
  - `customer-report-export` (from `wave1-customer-export`)
  - `plain-language-report` (from `plain-language-report`, `locality-aware-queries`, `report-conversion-quickwins`, `wave1-customer-export` gloss)
  - `url-intake` locality stance + query mix + operator overrides
- Added capabilities: `batch-export-runner`, `customer-web-report`
- Updated `geo-probe` visibility/rescore to match `brand_match` + `POST /api/runs/{id}/rescore`
- Retroactive archives under `openspec/changes/archive/2026-10-27-*` (brand-match-precision, batch-export-runner, customer-web-report, pdf-report-branding)
- Process: `openspec validate --strict` in AGENTS.md / ways-of-working; new `openspec-sync-specs` skill; `openspec/project.md`

## Validation

- `npx @fission-ai/openspec@latest validate --all --strict` — all six specs pass (strict)
- `python3 -m pytest eval -q` — 210 passed, 4 failed (pre-existing/env: fake probe models skipped without `OPENAI_API_KEY`; PDF model label expects "OpenAI search" while copy uses "ChatGPT search")
