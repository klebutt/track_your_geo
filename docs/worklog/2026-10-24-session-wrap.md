# Worklog — 2026-10-24 (session wrap)

## Merged today

- **PR #3** — `scripts/batch_export.py` generic batch runner + `apps/api/tygeo/brand.py` CTA
- **PR #4** — docs refresh
- **PR #5** — sample report built by default with fictional data, SAMPLE label, and booking CTA

Site redeployed; https://airecommend.co.uk/sample-report.pdf is live.

## Infrastructure

- **www → apex redirect** live via Cloudflare redirect rule (`www.airecommend.co.uk` → 301 → `airecommend.co.uk`)

## Wave-1 send status

- Send logs backfilled in vault: **125 events**
- **0 real replies**; 1 STOP, 1 bounce, 2 auto-replies
- **Unresolved:** Jeffrey Altman & Company wave-1 PDF may have been corrupted when sent

## Wave-2 prep

- **30 private limited accountancy firms** verified against Companies House
- Prospect list: Google Sheet in vault (not in git)
- Email draft: vault `reports/wave2-email-draft`
- Shared inboxes (info@ etc.) get "Hi there"

## NEXT (in order)

1. Kieran runs the 30-firm batch on his PC (~7.5 h, ~$20):
   - Dry run: `python scripts/batch_export.py --batch wave2 --input <vault>/reports/wave2-urls.csv --vault <vault> --dry-run`
   - Real run: same without `--dry-run`
2. `python site/build.py --vault <vault> --batch wave2`, then deploy from `site/`
3. Fill a one-line finding per firm into the email; check every `/r/` link loads
4. Run an inbox placement test
5. Get Kieran's explicit OK before any send

**Not for agents:** prospect list, send timing, and outreach copy remain human-only decisions.
