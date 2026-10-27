# Proposal: Customer web report site (retroactive)

**Status:** Retroactive documentation — behaviour shipped without an OpenSpec change in October 2026.

## Why

PRs [#1](https://github.com/klebutt/track_your_geo/pull/1), [#14](https://github.com/klebutt/track_your_geo/pull/14), and [#15](https://github.com/klebutt/track_your_geo/pull/15) launched the AI Recommend static site (`site/`), private `/r/<slug>/` report pages, markdown/HTML rendering parity with PDF, D1 view logging, and vault-driven batch page generation. PR [#5](https://github.com/klebutt/track_your_geo/pull/5) fixed the public sample report path (related to site build).

## What changed (as implemented)

- `site/build.py`, `site/public/`, `site/templates/report.html`, `site/functions/r/[[path]].js`
- `tygeo/customer_web_report.py` — HTML body mirroring PDF structure
- Cloudflare `_headers` noindex on `/r/*`; `/book` redirect in generated `_redirects`

## Capabilities

- New: `customer-web-report`

## Uncertainty

- Exact D1 database id and wrangler binding are deployment-specific; spec describes behaviour when `DB` is bound, not production IDs.
