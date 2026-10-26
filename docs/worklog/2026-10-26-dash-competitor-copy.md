# Dash display, directory competitor guard, low-score copy

## Shipped

- `format_query_display`: spaced dashes only; hyphenated words preserved.
- Query display normalisation on loss-entry lines (PDF + markdown).
- Block competitor match for `Your {name}` directory-style spans.
- Plain report weak-signal copy for 1–2 of 10 searches.

## Validation

- `pytest eval/test_brand_match.py eval/test_customer_export_display.py eval/test_plain_report.py`
