# Tasks: Recommendations Engine v1

- [x] **Backend Integration**
    - [x] Update `execute_run` in `analysis.py` to calculate `citation_gaps` and `sentiment_summary`.
    - [x] Update `run_recommendations` in `llm.py` with the enriched prompt.
    - [x] Re-enable the call to `run_recommendations` at the end of `execute_run`.
    - [x] Ensure results are saved to the `recommendations` table and associated with the `Run`.
- [x] **API & Schema**
    - [x] Update `RunOut` schema in `schemas.py` to include the `recommendations` list.
    - [x] Verify `GET /api/runs/{id}` now returns the generated advice.
- [x] **Frontend - Insights Section**
    - [x] Create a `RecommendationsList` component to display the cards.
    - [x] Create a `ScoreBreakdown` component explaining the 40/30/20/10 logic.
    - [x] Add the new "Insights & Optimization" section to the main dashboard layout.
- [x] **Validation**
    - [x] Run a full pilot for "Dishoom".
    - [x] Verify that recommendations are specific (e.g., mentioning real domains like 'The Infatuation' or specific competitors).
    - [x] Confirm the UI displays the score explanation and cards correctly.
