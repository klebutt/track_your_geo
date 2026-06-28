# Tasks: Multi-Brand YAML Loading

- [x] **Infrastructure**
    - [x] Add `TYGEO_PILOT_DIR: Path = Field(default=Path("pilots"))` to `Config` class in `apps/api/tygeo/config.py`.
    - [x] Create base `pilots/demo/` directory in the repo root.
- [x] **Data Migration**
    - [x] Create `pilots/demo/dishoom-london.yaml` with data from `hardcoded_pilots.py`.
    - [x] Create `pilots/demo/clio-uk.yaml`.
    - [x] Create `pilots/demo/sdl-surveying-uk.yaml`.
- [x] **Core Logic**
    - [x] Update `list_pilots()` in `apps/api/tygeo/pilots.py` to recursively scan `TYGEO_PILOT_DIR` for `.yaml` files.
    - [x] Use `PilotProfile.from_yaml()` for loading.
    - [x] Add error handling (log warning if a YAML file is malformed instead of crashing the whole list).
    - [x] Remove `HARDCODED_PILOT_SPECS` import and usage.
- [x] **Cleanup**
    - [x] Delete `apps/api/tygeo/hardcoded_pilots.py`.
    - [x] Update any imports pointing to it.
- [x] **Validation**
    - [x] Run `pytest` to ensure no regressions in pilot loading.
    - [x] Run a local smoke test: `GET http://localhost:8000/api/pilots` to confirm the 3 demo brands appear.
    - [x] Add a temporary `test-brand.yaml` to the folder and verify it appears in the list.
