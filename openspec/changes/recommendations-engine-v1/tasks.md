# Tasks: Recommendations Engine v1

- [ ] **Backend Integration**
    - [ ] Update `execute_run` in `analysis.py` to calculate `citation_gaps` and `sentiment_summary`.
    - [ ] Update `run_recommendations` in `llm.py` with the enriched prompt.
    - [ ] Re-enable the call to `run_recommendations` at the end of `execute_run`.
    - [ ] Ensure results are saved to the `recommendations` table and associated with the `Run`.
- [ ] **API & Schema**
    - [ ] Update `RunOut` schema in `schemas.py` to include the `recommendations` list.
    - [ ] Verify `GET /api/runs/{id}` now returns the generated advice.
- [ ] **Frontend - Insights Section**
    - [ ] Create a `RecommendationsList` component to display the cards.
    - [ ] Create a `ScoreBreakdown` component explaining the 40/30/20/10 logic.
    - [ ] Add the new "Insights & Optimization" section to the main dashboard layout.
- [ ] **Validation**
    - [ ] Run a full pilot for "Dishoom".
    - [ ] Verify that recommendations are specific (e.g., mentioning real domains like 'The Infatuation' or specific competitors).
    - [ ] Confirm the UI displays the score explanation and cards correctly.
