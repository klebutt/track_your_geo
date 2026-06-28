# OpenSpec Design: Dashboard History View

## 1. Backend Changes (`apps/api/`)

### API Endpoint Update
Modify `GET /api/runs` or add `GET /api/runs/latest` to support filtering by `pilot_id`.

**Option A (Recommended):** Update `GET /api/runs` to accept a `pilot_id` query parameter.
```python
@app.get("/api/runs")
def list_runs(pilot_id: str | None = None, limit: int = 20, db: Session = Depends(db_session)):
    query = db.query(Run)
    if pilot_id:
        query = query.filter(Run.pilot_id == pilot_id)
    return query.order_by(Run.created_at.desc()).limit(limit).all()
```

## 2. Frontend Changes (`apps/web/`)

### State Management
- When `selectedPilot` changes, trigger an effect to fetch the latest run for that ID.
- Store the history of runs for the chart.

### Components
- **Trend Chart:** Use a lightweight library (like `recharts` or `chart.js`) to plot:
    - X-Axis: `created_at` (Date)
    - Y-Axis 1: `visibility_rate` (0-100%)
    - Y-Axis 2: `total_citations` (sum of citation counts across all queries)
- **Run Selector:** (Optional) Add a "History" dropdown to let users manually switch the main view to an older run.

## 3. User Flow
1. User selects "Dishoom" from the dropdown.
2. Frontend calls `GET /api/runs?pilot_id=dishoom-london&limit=20`.
3. Frontend sets `activeRun` to `runs[0]`.
4. Dashboard instantly populates with the Dishoom results from the last run.
5. The Trend Chart renders the visibility scores from the remaining runs in the list.
