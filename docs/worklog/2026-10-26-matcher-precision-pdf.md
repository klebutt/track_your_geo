# Matcher precision + PDF display fixes

## Shipped

- Token-boundary matching; URLs stripped before match; short aliases (&lt;4 chars) uppercase-only.
- Generic `{Town} Accountants` rejects URL paths and lowercase listing prose; accepts proper-case / via / bold.
- `& Co` → `{prefix} Accountants` matching alias; batch export uses `manifest_firm` for PDF display.
- Regenerated PDFs use export report date; models footnote kept together; query dash spacing normalized.

## Validation

- `pytest eval/test_brand_match.py eval/test_customer_export_display.py eval/test_rescore.py eval/test_batch_export.py`
