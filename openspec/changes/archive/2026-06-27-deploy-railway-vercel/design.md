# Design: deploy-railway-vercel

## Architecture

```
Browser → Vercel (static SPA) → Railway (FastAPI, port 8000) → SQLite (Railway volume)
```

In production, the Vite frontend is a static build served by Vercel CDN. All API calls go directly to the Railway backend URL — there is no server-side proxy in production.

---

## Change 1 — CORS: allow configurable origins

**File:** `apps/api/tygeo/main.py`

Add `TYGEO_ALLOWED_ORIGINS` to `config.py` (comma-separated, default includes localhost):

```python
# config.py
tygeo_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

@property
def allowed_origins(self) -> list[str]:
    return [o.strip() for o in self.tygeo_allowed_origins.split(",") if o.strip()]
```

Update `main.py` to read from settings:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

On Railway, set env var: `TYGEO_ALLOWED_ORIGINS=https://<your-vercel-app>.vercel.app`

---

## Change 2 — Frontend API URL

**File:** `apps/web/src/App.tsx` (and any other `fetch` call sites)

Replace hardcoded `/api/...` paths with a base URL from env:

```typescript
// At top of App.tsx
const API_BASE = import.meta.env.VITE_API_URL ?? ""

// All fetch calls become:
fetchJson<T>(`${API_BASE}/api/pilots`)
fetchJson<T>(`${API_BASE}/api/runs`)
// etc.
```

**File:** `apps/web/.env.example` — add:
```
VITE_API_URL=
```

Locally: leave `VITE_API_URL` unset (empty string → relative paths → Vite proxy works as before).
On Vercel: set `VITE_API_URL=https://<your-railway-app>.up.railway.app`

---

## Change 3 — Railway configuration

**New file:** `apps/api/railway.json`

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
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
cmds = ["pip install -e '.[standard]'"]

[start]
cmd = "uvicorn tygeo.main:app --host 0.0.0.0 --port $PORT"
```

---

## Change 4 — SQLite persistence on Railway

Railway volumes mount at a path you define. Set:
- `TYGEO_DATABASE_URL=sqlite:////data/tygeo.db` (absolute path)
- Mount a Railway volume at `/data`

The `lifespan` handler already creates `data/` if it doesn't exist for relative paths; with an absolute path on a mounted volume it will persist across deploys.

---

## Change 5 — README: deploy instructions

Add a `## Deployment` section to `README.md` covering:
1. Railway: connect repo, set root directory to `apps/api`, set env vars
2. Vercel: connect repo, set root directory to `apps/web`, set `VITE_API_URL`
3. Required env vars table

---

## Environment variables reference

| Variable | Where | Value |
|---|---|---|
| `OPENAI_API_KEY` | Railway | Your OpenAI key |
| `TYGEO_ALLOWED_ORIGINS` | Railway | `https://<app>.vercel.app` |
| `TYGEO_DATABASE_URL` | Railway | `sqlite:////data/tygeo.db` |
| `TYGEO_MODEL` | Railway | `gpt-4o-mini` (default) |
| `VITE_API_URL` | Vercel | `https://<app>.up.railway.app` |
