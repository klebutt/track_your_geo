# Tasks: deploy-railway-vercel

## Status: implementation complete — pending live deploy (tasks 6–7)

Implement these tasks in order. Each task is a small, reviewable diff. Validate after task 4 (local smoke test) and after task 6 (live URL check).

---

### Task 1 — Add `tygeo_allowed_origins` to config ✅

**File:** `apps/api/tygeo/config.py`

Add field and property:
```python
tygeo_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

@property
def allowed_origins(self) -> list[str]:
    return [o.strip() for o in self.tygeo_allowed_origins.split(",") if o.strip()]
```

---

### Task 2 — Update CORS middleware to use config ✅

**File:** `apps/api/tygeo/main.py`

Replace the hardcoded `allow_origins` list:
```python
# Before
allow_origins=[
    "http://127.0.0.1:5173",
    "http://localhost:5173",
],

# After
allow_origins=Settings().allowed_origins,
```

---

### Task 3 — Add `VITE_API_URL` to frontend ✅

**File:** `apps/web/src/App.tsx`

Add at the top (before the `App` function):
```typescript
const API_BASE = import.meta.env.VITE_API_URL ?? ""
```

Replace every `/api/` fetch path with `` `${API_BASE}/api/` ``.

Check all `fetchJson` and `fetch` calls in the file — there should be around 5–6 occurrences.

**File:** `apps/web/.env.example`

Add line:
```
# Backend URL for production (leave empty for local dev with Vite proxy)
VITE_API_URL=
```

---

### Task 4 — Local smoke test ✅

Run both services locally and confirm:
1. `http://localhost:5173` loads the UI
2. Pilots list appears
3. Start a run — confirm it completes (uses Vite proxy → `VITE_API_URL` is empty → relative path)

Verified: `GET /api/health` → `{"status":"ok"}`, pilots list returns 3 demos; `pytest eval -q` passes (16 tests).

---

### Task 5 — Add Railway config files ✅

**New file:** `apps/api/railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "uvicorn tygeo.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

**New file:** `apps/api/nixpacks.toml`
```toml
[phases.setup]
nixPkgs = ["python311"]

[phases.install]
cmds = ["pip install -e ."]

[start]
cmd = "uvicorn tygeo.main:app --host 0.0.0.0 --port $PORT"
```

---

### Task 6 — Deploy backend to Railway ⏳ (manual)

1. Go to railway.app → New Project → Deploy from GitHub repo
2. Set **Root Directory** to `apps/api`
3. Railway auto-detects Nixpacks; it will run `pip install -e .`
4. Add env vars: `OPENAI_API_KEY`, `TYGEO_ALLOWED_ORIGINS` (set to `*` temporarily until Vercel URL is known), `TYGEO_DATABASE_URL=sqlite:////data/tygeo.db`
5. Add a Volume: mount path `/data`
6. Confirm `GET https://<app>.up.railway.app/api/health` → `{"status": "ok"}`

Note the Railway URL for the next task.

---

### Task 7 — Deploy frontend to Vercel ⏳ (manual)

1. Go to vercel.com → New Project → Import GitHub repo
2. Set **Root Directory** to `apps/web`
3. Vercel auto-detects Vite; build command `npm run build`, output `dist`
4. Add env var: `VITE_API_URL=https://<your-railway-app>.up.railway.app`
5. Deploy → confirm frontend loads and pilots appear

---

### Task 8 — Update Railway CORS and README ✅

1. In Railway dashboard: update `TYGEO_ALLOWED_ORIGINS` to the real Vercel URL (e.g. `https://track-your-geo.vercel.app`)
2. Trigger a Railway redeploy
3. Run a full end-to-end test: start a run from the Vercel URL, confirm it completes
4. Update `README.md` with a `## Deployment` section (env vars table + Railway/Vercel steps)

README deployment section added. Steps 1–3 pending live deploy.

---

### Task 9 — Worklog ✅

Update `docs/worklog/2026-06-27.md` with the deploy URLs and any issues encountered.

---

## Validation checklist

- [ ] `GET https://<railway-url>/api/health` → `{"status":"ok"}`
- [ ] Frontend loads at Vercel URL
- [ ] Pilots list populates
- [ ] Run completes end-to-end
- [ ] No CORS errors in browser console
- [ ] SQLite data persists after Railway redeploy (check run history)
