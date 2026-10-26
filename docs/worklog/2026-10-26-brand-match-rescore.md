# Brand mention matching + run rescore

## Shipped

- `tygeo/brand_match.py`: tolerant mention matching (&/and, apostrophe variants, Ltd suffix, markdown bold).
- Generic `{Town} Accountants` brands skip lowercase “looking for town accountants” phrasing only.
- `POST /api/runs/{id}/rescore` and `tygeo/rescore.py` recompute stored rows without probe LLM calls.
- `batch_export --regenerate` rescoring on by default (`--no-rescore` to skip); dry run previews score deltas when API is up.

## Validation

- `pytest eval/test_brand_match.py eval/test_rescore.py eval/test_batch_export.py`
