# Tasks: Structured Extraction



- [x] **Database & Models**

    - [x] Update `QueryResult` in `apps/api/tygeo/models.py` with `sentiment`, `mention_position`, and `relevance_score`.

    - [x] Run application to trigger automatic SQLite migrations.

- [x] **Extraction Logic**

    - [x] Implement `extract_mention_details` in `llm.py` using LiteLLM + `gpt-4o-mini`.

    - [x] Ensure it uses JSON mode / Response Format for reliable parsing.

- [x] **Pipeline Integration**

    - [x] Update the loop in `execute_run` to trigger extraction only when `is_visible` is true.

    - [x] Aggregate costs from the extraction call into the final run total.

- [x] **Scoring**

    - [x] Create `apps/api/docs/geo-scoring-formula.md` in the repo to match the version in Obsidian.

    - [x] Update `scoring.py` (or the relevant logic in `execute.py`) to calculate the `composite_score` using the new weighted formula (Visibility, Position, Sentiment, Citations).

- [x] **Frontend**

    - [x] Update the `RunOut` Pydantic model to include the new fields.

    - [x] Add "Sentiment" and "Position" columns to the dashboard table in `apps/web/`.

- [x] **Validation**

    - [x] Run `pytest` to ensure the new extraction function handles various response formats.

    - [x] Perform a local run with a known brand (e.g., Dishoom) and verify that "Positive" sentiment and "First" position are correctly extracted and displayed.

    - [x] Verify that runs where the brand is NOT mentioned do not trigger extraction calls (check `usage_log`).

