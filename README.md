# Track Your GEO — prototype

Local-only demo for **journeys 1, 2, and 4** from the product brief: discover visibility, diagnose gaps, and suggested actions. **Demo brands** (real company names, locations, competitors, and GEO query templates) are **hardcoded** in [`apps/api/tygeo/hardcoded_pilots.py`](apps/api/tygeo/hardcoded_pilots.py); change that file to swap the built-in targets. For how this score relates to consumer ChatGPT-style search, see [`docs/geo-scoring-realism.md`](docs/geo-scoring-realism.md). For human–agent session workflow (orient, plan, approve, validate, worklog), see [`AGENTS.md`](AGENTS.md).

## Prerequisites

- **Python 3.11+** (3.12+ recommended)
- **Node.js 20+** for the web UI and OpenSpec CLI (OpenSpec officially wants Node 20.19+)
- An **OpenAI API key** (or configure another provider supported by LiteLLM in code)

## Quick start (Windows)

From the repository root:

1. Create a virtual environment and install the app (example uses `tygeo-venv`):

```powershell
python -m venv tygeo-venv
.\tygeo-venv\Scripts\python.exe -m pip install -U pip setuptools wheel
.\tygeo-venv\Scripts\pip.exe install -e ".[dev,eval]"
```

2. Configure environment:

```powershell
Copy-Item .env.example .env
# Edit .env: set OPENAI_API_KEY and optionally TYGEO_MODEL (default gpt-4o-mini)
```

3. Start the API (terminal A), from repo root:

```powershell
.\tygeo-venv\Scripts\uvicorn.exe tygeo.main:app --reload --host 127.0.0.1 --port 8000
```

4. Install and start the web UI (terminal B):

```powershell
cd apps\web
npm install
npm run dev
```

5. Open the URL printed by Vite (usually `http://localhost:5173`), pick a **demo brand** from the dropdown, optionally override brand/location, and click **Run analysis**.

Alternatively run both processes using [scripts/dev.ps1](scripts/dev.ps1).

## Repository layout

| Path | Purpose |
|------|---------|
| [apps/api/tygeo/](apps/api/tygeo/) | FastAPI app, LiteLLM calls, SQLite persistence; built-in demo brands live in [`hardcoded_pilots.py`](apps/api/tygeo/hardcoded_pilots.py) |
| [apps/web/](apps/web/) | Vite + React dashboard |
| [pilot/](pilot/) | Optional folder for future YAML pilots; the prototype **does not** read YAML from here today |
| [openspec/](openspec/) | OpenSpec specs and change proposals |
| [eval/](eval/) | Pytest + DeepEval checks |
| [docs/geo-scoring-realism.md](docs/geo-scoring-realism.md) | Limits of the prototype score vs real assistant search; ways to improve fidelity |
| [docs/worklog/](docs/worklog/) | Session summaries and suggested next steps |
| [product_brief.md](product_brief.md) | Product context |

## OpenSpec

This repo uses [Fission-AI OpenSpec](https://openspec.dev/). Slash commands live under `.cursor/commands/` (for example `/opsx:propose`). After pulling changes, restart Cursor so commands register.

## Evaluation (DeepEval + pytest)

```powershell
.\tygeo-venv\Scripts\pytest.exe eval -q
```

DeepEval is used for a **deterministic substring metric** on golden snippets (no extra LLM calls in that test). Add API-based metrics later as prompts stabilize.

## uv (optional)

If you use [uv](https://github.com/astral-sh/uv): `uv sync` then `uv run pip install -e ".[dev,eval]"` is not needed — use `uv sync --extra dev --extra eval` once `uv` supports extras on your machine.

## Data

SQLite database file defaults to `./data/tygeo.db` (created on first run). Add `data/` to backups if you care about historical runs.
