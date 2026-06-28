# OpenSpec Proposal: Multi-Brand YAML Loading

## Goal
Enable dynamic brand/pilot loading from YAML files in the `pilots/` directory, replacing the hardcoded demo brands. This allows adding real customer pilots without editing source code or redeploying the backend.

## Problem
Currently, demo brands are hardcoded in `hardcoded_pilots.py`. Adding a new brand requires a code change and a redeploy of the Railway API. The existing YAML loading logic in `pilots.py` is bypassed and incomplete.

## Solution
1. **Refactor `list_pilots`** to scan a configurable directory (default: `pilots/`) for `.yaml` files.
2. **Merge** YAML-loaded brands with the existing hardcoded ones (or move hardcoded brands to YAML files entirely).
3. **Ensure idempotency:** Loading logic should be safe to run on every API request or cached per session.
4. **Validation:** Use the existing Pydantic `PilotProfile` to validate YAML structure.

## Technical Scope
- Update `tygeo/config.py` to include `TYGEO_PILOT_DIR`.
- Update `tygeo/pilots.py` to implement the scanning and loading logic.
- (Optional but recommended) Move `dishoom-london`, `clio-uk`, and `sdl-surveying-uk` to YAML files in `pilots/demo/`.

## Impact
- **No-code pilots:** Sam or the user can add brands via simple file uploads.
- **UI dropdown:** Automatically reflects all available brands.
- **Scalability:** Foundation for a future "Add Brand" UI.

## Cost
$0. No LLM calls.
