# Proposal: PDF report branding and customer copy (retroactive)

**Status:** Retroactive documentation — behaviour shipped without an OpenSpec change in October 2026.

## Why

PRs [#7](https://github.com/klebutt/track_your_geo/pull/7), [#8](https://github.com/klebutt/track_your_geo/pull/8), and [#12](https://github.com/klebutt/track_your_geo/pull/12) added branded PDF headers/footers, cover report date (including regenerate export date), sample callout styling, `/book` redirect wiring via `tygeo.brand`, customer `display_name` on the title block, and renamed snapshot visibility labeling to "Mentioned in AI replies" with per-reply percentage wording. September `customer-report-export` and `plain-language-report` archives predate this branding.

## What changed (as implemented)

- `tygeo/customer_export.py` — `_BrandedPDF` header/footer, cover block, sample callout, snapshot labels, `export_brand_name`, `_report_export_date`
- `tygeo/brand.py` — shared booking colours and CTA constants
- `tygeo/plain_report.py` — `INDEX_NOTE`, `DEEPER_INSIGHTS_LEAD` book-a-call copy (no prices)
- `site/build.py` — `_redirects` `/book` 302

## Capabilities

- Modified: `customer-report-export`, `plain-language-report` (gloss/CTA; see September archives for earlier plain-report requirements)

## Uncertainty

- PR #7 title mentions booking CTA on PDF; the visible book-a-call string is primarily in deeper-insights markdown/PDF sections via `DEEPER_INSIGHTS_LEAD`, not a separate footer CTA block on every page.
