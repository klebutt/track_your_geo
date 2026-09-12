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

- **Active change:** [plain-language-report](openspec/changes/plain-language-report/) — implemented; archive next
- **Priorities (in order):**
  1. Lock locality-aware query open questions (see EOD worklog)
  2. Archive `plain-language-report`
  3. Propose + implement locality-aware accountant queries (stance infer, local vs UK-wide mix, local competitors)
  4. Top 10 vault prospects via **local** URL→report (do not copy prospect list into git)
  5. Railway/prod parked until WTP validated

- **Live URLs:** Frontend https://track-your-geo.vercel.app/ · API https://trackyourgeo-production.up.railway.app (prod not required)
- **Context:** EOD [docs/worklog/2026-09-12-eod.md](docs/worklog/2026-09-12-eod.md). Vault `status.md` + `accountant-prospects.md`.

When implementing, align with OpenSpec capabilities and prefer small, reviewable changes.
