## 1. Matching

- [x] 1.1 Implement `brand_match` normalization and phrase guards
- [x] 1.2 Wire `analyze_response` and probe persistence to new matcher
- [x] 1.3 Add eval coverage in `eval/test_brand_match.py`

## 2. Rescore

- [x] 2.1 Implement `preview_rescore_run` / `rescore_run`
- [x] 2.2 Expose `POST /api/runs/{id}/rescore`
- [x] 2.3 Add `eval/test_rescore.py`

## 3. Batch integration

- [x] 3.1 Call rescore during `batch_export --regenerate` (default on)

## 4. Specs (retroactive)

- [x] 4.1 Merge delta into `openspec/specs/geo-probe/spec.md`
