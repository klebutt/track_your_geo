# Agent context

Track Your GEO: deployed MVP for GEO visibility probing. Agents collaborate with humans via **orient → plan (approve) → implement → validate → worklog**.

## Cursor vs Obsidian

This **repo** is the build system (code, OpenSpec, worklogs, formula). The **Obsidian vault** is the thinking system (strategy, personas, session status). Do not copy OpenSpec, formula, or worklogs into the vault. Full split: [docs/ways-of-working.md](docs/ways-of-working.md). Code-change workflow: [Working through Grok Bot](docs/ways-of-working.md#working-through-grok-bot). Vault path: `G:\My Drive\Obsidian\projects\track-your-geo\` (start at `status.md`).

## Collaboration workflow

1. **Orient** — Vault `status.md` (session goal) if accessible; latest [docs/worklog/](docs/worklog/); active [openspec/changes/](openspec/changes/); relevant [openspec/specs/](openspec/specs/).
2. **Clarify** — Restate objective, scope, out-of-scope; ask if unclear.
3. **Plan** — Post a **Plan (awaiting approval)** block (template below). **Do not change product code until the human approves**, except trivial fixes they delegated in the same message.
4. **Spec** — Non-trivial work: OpenSpec propose/explore/apply skills (see `.cursor/skills/openspec-*`). Trivial fixes: skip new change folder.
5. **Implement** — Small, reviewable diffs; follow approved plan and task list.
6. **Validate** — `pytest eval -q`; manual UI smoke if UI/API touched; note LLM cost impact.
7. **Record** — Update [docs/worklog/](docs/worklog/); archive OpenSpec change when done. Note doc impact in the PR body; Grok Bot updates the vault.

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

- From repo root: `pytest eval -q` (or `.\tygeo-venv\Scripts\pytest.exe eval -q` on Windows)
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

## Current focus (Grok Bot keeps this in sync with vault `status.md`)

*Updated 2026-10-24*

- **Phase:** Wave 2 prep. Wave 1 closed (~50 PDF reports emailed Sept, 47 bumps 7–12 Oct, 0 real replies).
- **In flight:** generic batch runner PR (replaces `scripts/wave1_*_export.py` for new batches; runs on Kieran's PC).
- **Next (in order):**
  1. Merge batch runner → Kieran runs ~20 new **Ltd/LLP** accountancy reports (no sole traders/partnerships: PECR)
  2. Build private `/r/<slug>/` pages with `site/build.py` (hash-gate hosted PDF vs vault PDF; `wave2-links.csv` stays in vault)
  3. Kieran deploys (`wrangler pages deploy site/dist --project-name airecommend`)
- **Shipped 24 Oct:** `site/` live at https://airecommend.co.uk (Cloudflare Pages `airecommend`, D1 `airecommend-log` logs `/r/*` opens). PR #1 site, PR #2 PECR privacy wording. CTA = 15-min Google Calendar booking link. Footer: "AI Recommend is a trading name of Kieran Le Butt".
- **Live app:** https://track-your-geo.vercel.app/ (Railway API https://trackyourgeo-production.up.railway.app currently returns 404; parked)
- **Locked:** `gpt-5-search-api` + Perplexity + Gemini (3-model); no prices in reports/site/email for wave 2; no prospect data or report output in git (`site/dist/` gitignored).
- **Not for agents:** deploys, DNS, prospect emails. Kieran only. See [Working through Grok Bot](docs/ways-of-working.md#working-through-grok-bot).

When implementing, align with OpenSpec capabilities and prefer small, reviewable changes.
