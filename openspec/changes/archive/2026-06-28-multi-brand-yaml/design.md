# OpenSpec Design: Multi-Brand YAML Loading

## 1. Config Change
Add `TYGEO_PILOT_DIR` to `tygeo/config.py`.
- Default: `Path("pilots")`
- Should be configurable via environment variable for Railway (e.g. `/data/pilots` if using a volume).

## 2. Directory Structure
```text
pilots/
  demo/
    dishoom.yaml
    clio.yaml
    sdl.yaml
  customers/
    (future customer files)
```

## 3. Implementation in `tygeo/pilots.py`

### `list_pilots` refactor:
1. Initialize an empty list.
2. If `TYGEO_PILOT_DIR` exists:
   - Walk the directory recursively.
   - For each `.yaml` or `.yml` file:
     - Try `PilotProfile.from_yaml(file_path)`.
     - Append to the list.
3. (Optional) Append `HARDCODED_PILOT_SPECS` for backward compatibility or during migration.
4. Return the list.

### `load_pilot` refactor:
1. Call `list_pilots`.
2. Find by `id`.

## 4. Migration Plan
1. Create `pilots/demo/` directory.
2. Export `dishoom`, `clio`, and `sdl` to YAML files.
3. Verify `list_pilots` returns them correctly.
4. Delete `hardcoded_pilots.py`.

## 5. UI Alignment
No changes needed. The `GET /api/pilots` endpoint will automatically return the new list, and the frontend dropdown will populate.
