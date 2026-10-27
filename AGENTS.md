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
6. **Validate** — `openspec validate --all --strict` (install CLI via `npx --yes @fission-ai/openspec@latest` if needed); `pytest eval -q`; manual UI smoke if UI/API touched; note LLM cost impact.
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
- **Score:** Normalized phrase visibility gate (`tygeo/brand_match`) + LLM extraction (sentiment, position) for composite GEO score; not consumer ChatGPT parity unless explicitly scoped.
- **Demos:** YAML pilots under [apps/api/pilots/](apps/api/pilots/) (default `pilots/demo/`).
- **Recommendations:** Enabled after each run — enriched LLM call using sentiment, position, citation gaps, and competitor signals (~$0.005/run). See §4 **Insights & optimization** in the dashboard.

## OpenSpec

- **Canonical behavior:** [openspec/specs/](openspec/specs/)
- **Active work:** [openspec/changes/](openspec/changes/)
- **Explore** (ideas, no code): `openspec-explore` skill
- **Propose** (new change artifacts): `openspec-propose` skill
- **Implement** (tasks): `openspec-apply-change` skill
- **Archive** (done): `openspec-archive-change` skill
- **Sync deltas → main specs:** `openspec-sync-specs` skill (used when archiving or backfilling specs)

Use a new change when behavior, APIs, or user-visible contracts change materially.

**Cloud-agent PRs:** Every PR that changes product behaviour MUST include an OpenSpec change (propose → implement → archive with synced specs) **or** an explicit line in the PR body: `Trivial — no OpenSpec change` (docs-only / comment-only / CI-only).

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

- **Merged today (2026-10-24):** PR #3 (batch runner + CTA), PR #4 (docs refresh), PR #5 (sample report with SAMPLE label)
- **Live:** https://airecommend.co.uk/sample-report.pdf · www→apex 301 redirect via Cloudflare
- **Wave-1:** sent; send logs backfilled in vault (125 events, 0 real replies, 1 STOP, 1 bounce, 2 auto-replies); Jeffrey Altman PDF corruption unresolved
- **Wave-2:** 30 private limited accountancy firms; contacts verified vs Companies House; list + email draft in vault (not in git); shared inboxes get "Hi there"
- **NEXT (in order):**
  1. Kieran runs 30-firm batch on his PC (~7.5 h, ~$20): dry run first (`python scripts/batch_export.py --batch wave2 --input <vault>/reports/wave2-urls.csv --vault <vault> --dry-run`), then real run
  2. `python site/build.py --vault <vault> --batch wave2`, deploy from `site/`
  3. Fill one-line finding per firm into email; verify every `/r/` link loads
  4. Run inbox placement test
  5. Get Kieran's explicit OK before any send
- **Shipped 24 Oct:** `site/` live at https://airecommend.co.uk (Cloudflare Pages `airecommend`, D1 `airecommend-log` logs `/r/*` opens). PR #1 site, PR #2 PECR privacy wording. Report CTA = "Book a free 15-minute call … or email kieran@airecommend.co.uk" (link in `apps/api/tygeo/brand.py`). Footer: "AI Recommend is a trading name of Kieran Le Butt".
- **Context:** [docs/worklog/2026-10-24-session-wrap.md](docs/worklog/2026-10-24-session-wrap.md) · vault `decisions/2026-09-13-bulk-probe-economics.md`
- **Live app:** https://track-your-geo.vercel.app/ (Railway API https://trackyourgeo-production.up.railway.app currently returns 404; parked)
- **Locked:** `gpt-5-search-api` + Perplexity + Gemini (3-model); no prices in reports/site/email for wave 2; no prospect data or report output in git (`site/dist/` gitignored).
- **Not for agents:** deploys, DNS, prospect emails. Kieran only. See [Working through Grok Bot](docs/ways-of-working.md#working-through-grok-bot).

When implementing, align with OpenSpec capabilities and prefer small, reviewable changes.
