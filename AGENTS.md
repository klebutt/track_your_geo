# Agent context

Track Your GEO: local MVP for GEO visibility probing. Agents collaborate with humans via **orient → plan (approve) → implement → validate → worklog**.

## Collaboration workflow

1. **Orient** — Latest [docs/worklog/](docs/worklog/) entry; active [openspec/changes/](openspec/changes/); relevant [openspec/specs/](openspec/specs/).
2. **Clarify** — Restate objective, scope, out-of-scope; ask if unclear.
3. **Plan** — Post a **Plan (awaiting approval)** block (template below). **Do not change product code until the human approves**, except trivial fixes they delegated in the same message.
4. **Spec** — Non-trivial work: OpenSpec propose/explore/apply skills (see `.cursor/skills/openspec-*`). Trivial fixes: skip new change folder.
5. **Implement** — Small, reviewable diffs; follow approved plan and task list.
6. **Validate** — `pytest eval -q`; manual UI smoke if UI/API touched; note LLM cost impact.
7. **Record** — Update [docs/worklog/](docs/worklog/); archive OpenSpec change when done.

### Plan (awaiting approval) template

- **Objective:**
- **In scope / out of scope:**
- **OpenSpec change:**
- **Approach:**
- **Files likely touched:**
- **Risks / product notes:**
- **Validation:**
- **Worklog:**

## Product guardrails

- [product_brief.md](product_brief.md) — journeys and MVP scope.
- [docs/geo-scoring-realism.md](docs/geo-scoring-realism.md) — scoring limits and improvement options; required for probe/score/UI work.
- **Probes:** brand-neutral questions only (no brand name in prompt text).
- **Score:** Substring visibility gate + LLM extraction (sentiment, position) for composite GEO score; not consumer ChatGPT parity unless explicitly scoped.
- **Demos:** YAML pilots under [apps/api/pilots/](apps/api/pilots/) (default `pilots/demo/`).
- **Recommendations:** Enabled after each run — enriched LLM call using sentiment, position, citation gaps, and competitor signals (~$0.005/run). See §4 **Insights & optimization** in the dashboard.

## OpenSpec

- **Canonical behavior:** [openspec/specs/](openspec/specs/)
- **Active work:** [openspec/changes/](openspec/changes/)
- **Explore** (ideas, no code): `openspec-explore` skill
- **Propose** (new change artifacts): `openspec-propose` skill
- **Implement** (tasks): `openspec-apply-change` skill
- **Archive** (done): `openspec-archive-change` skill

Use a new change when behavior, APIs, or user-visible contracts change materially.

## Testing

- From repo root: `.\tygeo-venv\Scripts\pytest.exe eval -q`
- Prefer deterministic tests in [eval/](eval/); avoid live LLM in default tests.
- Manual: API port 8000 + Vite 5173 ([README.md](README.md)).

## Key references

| Topic | Location |
|--------|----------|
| Product intent | [product_brief.md](product_brief.md) |
| Scoring realism | [docs/geo-scoring-realism.md](docs/geo-scoring-realism.md) |
| Composite score formula | [apps/api/docs/geo-scoring-formula.md](apps/api/docs/geo-scoring-formula.md) |
| Session history | [docs/worklog/](docs/worklog/) |
| Behavior specs | [openspec/specs/](openspec/specs/) |
| Active proposals | [openspec/changes/](openspec/changes/) |

## Current focus (update by humans)

- **Active change:** _(none)_
- **Priorities (in order):**
  1. Calibration panel vs consumer ChatGPT (see [docs/geo-scoring-realism.md](docs/geo-scoring-realism.md))

- **Live URLs:** Frontend https://track-your-geo.vercel.app/ · API https://trackyourgeo-production.up.railway.app
- **Context:** See [docs/worklog/2026-06-28.md](docs/worklog/2026-06-28.md) — multi-LLM, YAML pilots, async runs, dashboard history, structured extraction, **recommendations engine v1** (insights section + enriched advice) verified in prod.

When implementing, align with OpenSpec capabilities and prefer small, reviewable changes.
