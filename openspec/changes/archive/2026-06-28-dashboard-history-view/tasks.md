# Tasks: Dashboard History View

- [x] **Backend**
    - [x] Update `api_list_runs` in `apps/api/tygeo/main.py` to accept `pilot_id: str | None = None`.
    - [x] Add the SQLAlchemy `.filter()` logic for `pilot_id`.
    - [x] Verify locally: `GET /api/runs?pilot_id=dishoom-london&limit=1` returns the latest Dishoom run.
- [x] **Frontend - Auto-Load**
    - [x] In `App.tsx` (or your main view), add an `useEffect` that triggers when the brand dropdown changes.
    - [x] Fetch the latest run for that ID.
    - [x] If a run exists, set it as the active run state (populating the table).
- [x] **Frontend - Trend Chart**
    - [x] Install a charting library (e.g., `npm install recharts`).
    - [x] Create a `TrendChart` component.
    - [x] Map the list of historical runs to chart data (Date vs. Visibility %).
    - [x] Add the chart to the Dashboard (above or below the results table).
- [x] **Validation**
    - [x] Select a brand, confirm the UI populates immediately with the last run data.
    - [x] Verify the chart shows at least one data point for the current brand.
    - [x] Run a new analysis and verify the chart updates with the new point.
