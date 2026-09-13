# Agent context

Track Your GEO: deployed MVP for GEO visibility probing. Agents collaborate with humans via **orient → plan (approve) → implement → validate → worklog**.

## Cursor vs Obsidian

This **repo** is the build system (code, OpenSpec, worklogs, formula). The **Obsidian vault** is the thinking system (strategy, personas, session status). Do not copy OpenSpec, formula, or worklogs into the vault. Full split: [docs/ways-of-working.md](docs/ways-of-working.md). Vault path: `G:\My Drive\Obsidian\projects\track-your-geo\` (start at `status.md`).

## Collaboration workflow

1. **Orient** — Vault `status.md` (session goal) if accessible; latest [docs/worklog/](docs/worklog/); active [openspec/changes/](openspec/changes/); relevant [openspec/specs/](openspec/specs/).
2. **Clarify** — Restate objective, scope, out-of-scope; ask if unclear.
3. **Plan** — Post a **Plan (awaiting approval)** block (template below). **Do not change product code until the human approves**, except trivial fixes they delegated in the same message.
4. **Spec** — Non-trivial work: OpenSpec propose/explore/apply skills (see `.cursor/skills/openspec-*`). Trivial fixes: skip new change folder.
5. **Implement** — Small, reviewable diffs; follow approved plan and task list.
6. **Validate** — `pytest eval -q`; manual UI smoke if UI/API touched; note LLM cost impact.
7. **Record** — Update [docs/worklog/](docs/worklog/); archive OpenSpec change when done. Remind the human to refresh vault `status.md` if the session goal or live state changed.

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
| Ways of working | [docs/ways-of-working.md](docs/ways-of-working.md) |
| Product intent | [product_brief.md](product_brief.md) |
| Scoring realism | [docs/geo-scoring-realism.md](docs/geo-scoring-realism.md) |
| Composite score formula | [apps/api/docs/geo-scoring-formula.md](apps/api/docs/geo-scoring-formula.md) |
| Session history | [docs/worklog/](docs/worklog/) |
| Behavior specs | [openspec/specs/](openspec/specs/) |
| Active proposals | [openspec/changes/](openspec/changes/) |
| Session / strategy (vault) | `G:\My Drive\Obsidian\projects\track-your-geo\status.md` |

## Current focus (update by humans; keep in sync with vault `status.md`)

- **Active change:** [wave1-customer-export](openspec/changes/wave1-customer-export/) — shipped; first-5 check done; overnight remainder pending
- **Also open:** [report-conversion-quickwins](openspec/changes/report-conversion-quickwins/), [locality-aware-queries](openspec/changes/locality-aware-queries/) — archive when ready
- **Priorities (in order):**
  1. After PDF check: overnight remainder `scripts/wave1_bulk_export.py --offset 5 --limit 45 --skip-pause --reuse-completed`
  2. BD sheets from vault `reports/wave1-manifest.csv` + `wave1-pdfs/`
  3. Archive OpenSpec changes when confident

- **Live URLs:** Frontend https://track-your-geo.vercel.app/ · API https://trackyourgeo-production.up.railway.app (prod not required)
- **Context:** [docs/worklog/2026-09-13-wave1-customer-export.md](docs/worklog/2026-09-13-wave1-customer-export.md) · vault `decisions/2026-09-13-bulk-probe-economics.md`
- **OpenAI search TPM:** 6k on `gpt-5-search-api`; pacing keeps 30/30 (~15 min/firm)
- **Locked:** Option A full 3-model; do not copy `accountant-prospects` into git
- **Wave-1 check:** first 5 complete (~$3.66); say continue overnight for offset 5+

When implementing, align with OpenSpec capabilities and prefer small, reviewable changes.
