# Fix sample-report.pdf for airecommend.co.uk

**Date:** 2026-10-24

## Problem

The homepage at https://airecommend.co.uk has two buttons linking to `/sample-report.pdf`, which 404s because:

1. The sample is only built when `python site/build.py --sample` is run
2. The documented build doesn't pass `--sample`

When built, the sample PDF had additional issues:

- Used real competitor names (Beever and Struthers, DJH Mitten Clarke, Xeinadin)
- Inconsistent numbers: "3 of 5 questions" but "Visibility 40%"
- Old CTA: "Reply if any of these would help" instead of current booking link
- No clear SAMPLE label

## Changes

### 1. Fictional competitors only (`pilots/gold/riverside-accountants.yaml`)

Replaced real competitor names with fictional ones:
- Northside Partners
- Summit Business Services
- Clearview Accounting

### 2. Consistent sample data (`site/build.py`)

Fixed query_results so 2 of 5 queries show brand mentioned = 40% visibility, matching `visibility_rate: 0.4`.

### 3. Real CTA in sample

Post-process sample markdown/PDF to replace "Reply if any of these would help" with:
- Book a free 15-minute call: [booking link]
- Or email kieran@airecommend.co.uk

### 4. SAMPLE label

Added blockquote near the top: "SAMPLE REPORT — This report uses fictional data for demonstration purposes."

### 5. Sample built by default

Changed `--sample` flag to `--no-sample`. Sample report is now built by default since the homepage requires it.

### 6. Tests

Added `TestSampleReportBuild` class with tests:
- `test_sample_pdf_exists` — PDF exists in dist root
- `test_sample_page_exists` — /r/sample/ page exists
- `test_sample_pdf_no_reply_if` — No "Reply if" wording
- `test_sample_has_booking_link` — Real CTA present
- `test_sample_labeled_as_sample` — SAMPLE label present
- `test_sample_has_noindex` — Proper noindex meta
- `test_sample_uses_fictional_competitors` — No real firm names

## Build & Deploy

```bash
# Build (sample is automatic)
python site/build.py

# Deploy
cd site
npx wrangler pages deploy dist --project-name airecommend --branch main
```

## Files changed

- `apps/api/pilots/gold/riverside-accountants.yaml` — fictional competitors
- `site/build.py` — consistent data, real CTA, SAMPLE label, default sample
- `eval/test_site_build.py` — new TestSampleReportBuild tests
- `README.md` — updated build docs (--sample → --no-sample)
