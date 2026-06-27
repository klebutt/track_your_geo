# Proposal: deploy-railway-vercel

## What

Deploy the Track Your GEO prototype to a live public URL:
- FastAPI backend → **Railway** (free tier)
- Vite/React frontend → **Vercel** (free tier)

## Why

The prototype currently runs only on a local machine. A live URL is a prerequisite for:
- Customer demos and trials (Sam's outreach)
- Running real visibility queries against actual LLM APIs
- Testing multi-LLM and citation features in a real environment

Nothing else on the roadmap is demoed or validated without this.

## Scope

**In scope:**
- Fix CORS to allow the Vercel frontend origin
- Add `VITE_API_URL` env var so the frontend hits the Railway backend in production
- Add `railway.json` to configure the backend start command and health check
- Add a `nixpacks.toml` (or `Procfile`) to pin the Python build on Railway
- Mount a Railway volume for SQLite persistence across deploys
- Document the deploy steps in README

**Out of scope:**
- Migrating from SQLite to Postgres (defer)
- Auth or access control (defer)
- Custom domain
- Any feature changes

## Success criteria

1. `GET https://<railway-url>/api/health` returns `{"status": "ok"}`
2. Frontend loads at `https://<vercel-url>` and can list pilots
3. A run completes end-to-end (probes sent, visibility score returned) via the deployed URL
