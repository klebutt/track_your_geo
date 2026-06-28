# Tasks: Dashboard History View

- [ ] **Backend**
    - [ ] Update `api_list_runs` in `apps/api/tygeo/main.py` to accept `pilot_id: str | None = None`.
    - [ ] Add the SQLAlchemy `.filter()` logic for `pilot_id`.
    - [ ] Verify locally: `GET /api/runs?pilot_id=dishoom-london&limit=1` returns the latest Dishoom run.
- [ ] **Frontend - Auto-Load**
    - [ ] In `App.tsx` (or your main view), add an `useEffect` that triggers when the brand dropdown changes.
    - [ ] Fetch the latest run for that ID.
    - [ ] If a run exists, set it as the active run state (populating the table).
- [ ] **Frontend - Trend Chart**
    - [ ] Install a charting library (e.g., `npm install recharts`).
    - [ ] Create a `TrendChart` component.
    - [ ] Map the list of historical runs to chart data (Date vs. Visibility %).
    - [ ] Add the chart to the Dashboard (above or below the results table).
- [ ] **Validation**
    - [ ] Select a brand, confirm the UI populates immediately with the last run data.
    - [ ] Verify the chart shows at least one data point for the current brand.
    - [ ] Run a new analysis and verify the chart updates with the new point.
