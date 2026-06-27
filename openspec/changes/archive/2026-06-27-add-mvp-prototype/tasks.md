# Tasks: MVP prototype

## Done in implementation

- [x] Repo skeleton (`apps/api`, `apps/web`, `pilot/`, `eval/`, `scripts/dev.ps1`, `README.md`, `.env.example`)
- [x] OpenSpec change scaffold + proposal/design/tasks
- [x] Pilot YAML schema + two example pilots
- [x] FastAPI routes: health, pilots, create/list/get runs
- [x] LiteLLM integration + per-call cost aggregation
- [x] SQLite models + ordered relationships for stable UI
- [x] React dashboard with disclaimer and cost summary
- [x] Pytest + DeepEval substring metric smoke tests

## Next iterations (not blocking demo)

- [ ] Add optional LLM-as-judge for mention verification (DeepEval GEval)
- [ ] Multi-model probe + aggregate view
- [ ] CI workflow (ruff + pytest) when repo is on GitHub
