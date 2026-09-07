# Ways of working — Cursor vs Obsidian

Track Your GEO uses two complementary systems. **Do not duplicate canonical docs across both.**

## Roles

| Tool | Role | Owns |
|------|------|------|
| **Cursor + this GitHub repo** | Build system | Code, OpenSpec, APIs/UI, eval tests, [docs/worklog/](worklog/), [scoring formula](../apps/api/docs/geo-scoring-formula.md), deploy config, agent instructions ([AGENTS.md](../AGENTS.md)) |
| **Obsidian vault** (`G:\My Drive\Obsidian`) | Thinking system | Strategy, personas, competitive research, gap analysis, **session status**, Sam-facing narrative |
| **Zapia** | Session glue | Propose session goals from vault status; update vault after sessions — not this repo |

**Rule of thumb:** needed to change product behaviour → **repo**. Needed to decide *what* to build → **vault**.

Vault project folder: `projects/track-your-geo/` (especially `status.md` and `next-development-phases.md`). Full ritual: vault `workflow.md`.

## Session ritual

1. **Orient (vault)** — Read Obsidian `status.md`; agree one goal.
2. **Mirror (repo)** — Put that goal in [AGENTS.md](../AGENTS.md) → Current focus when agents will implement.
3. **Build (Cursor)** — Follow AGENTS: plan (approve) → OpenSpec if needed → implement → `pytest eval -q`.
4. **Record** — Product behaviour changed → dated file under [docs/worklog/](worklog/). Session state → update vault `status.md`. Do **not** copy OpenSpec or formula files into Obsidian.

## Product brief

[product_brief.md](../product_brief.md) in this repo is what coding agents use. The vault may keep a planning copy — **sync both when vision or MVP scope changes.**
