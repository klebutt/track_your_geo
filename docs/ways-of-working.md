# Ways of working — Cursor vs Obsidian

Track Your GEO uses two complementary systems. **Do not duplicate canonical docs across both.**

## Roles

| Tool | Role | Owns |
|------|------|------|
| **Cursor + this GitHub repo** | Build system | Code, OpenSpec, APIs/UI, eval tests, [docs/worklog/](worklog/), [scoring formula](../apps/api/docs/geo-scoring-formula.md), deploy config, agent instructions ([AGENTS.md](../AGENTS.md)) |
| **Obsidian vault** (`G:\My Drive\Obsidian`) | Thinking system | Strategy, personas, competitive research, gap analysis, experiments, **session status** |
| **Grok Bot** | Primary assistant | Routes work to teammate bots; briefs Cursor cloud agents; keeps vault `status.md` and repo AGENTS.md *Current focus* in sync |

**Rule of thumb:** needed to change product behaviour → **repo**. Needed to decide *what* to build → **vault**.

Vault project folder: `projects/track-your-geo/` (especially `status.md` and `next-development-phases.md`). Full ritual: vault `workflow.md`.

## Session ritual

1. **Orient (vault)** — Read Obsidian `status.md`; agree one goal.
2. **Mirror (repo)** — Put that goal in [AGENTS.md](../AGENTS.md) → Current focus when agents will implement.
3. **Build (Cursor)** — Follow AGENTS: plan (approve) → OpenSpec if needed → implement → `pytest eval -q`.
4. **Record** — Product behaviour changed → dated file under [docs/worklog/](worklog/). Session state → update vault `status.md`. Do **not** copy OpenSpec or formula files into Obsidian.

## Product brief

[product_brief.md](../product_brief.md) in this repo is what coding agents use. The vault may keep a planning copy — **sync both when vision or MVP scope changes.**

## Working through Grok Bot

*(from 2026-10-24)*

Kieran works mainly through **Grok Bot**, his primary assistant. Grok Bot routes work and keeps docs current; it does not replace Kieran's approvals.

| Who | Owns |
|-----|------|
| **Kieran** | Decisions, PR merges, deploys, DNS, report runs (on his PC), every prospect send |
| **Grok Bot** | Routing, rollups, briefing Cursor cloud agents, keeping vault `status.md` + this repo's AGENTS.md *Current focus* in sync |
| **Product Analyst** (bot) | Experiment design, thresholds, readouts |
| **Sales Outreach** (bot) | Report packaging, outbound copy, reply handling, WTP logging |
| **Business Development Manager** (bot) | AgentMail/domain, contacts, send queue, send ops |
| **Cursor cloud agents** | Code changes on a branch → PR (with OpenSpec change + worklog when behaviour changes) |

**Flow for code:** Grok Bot writes a self-contained brief (goal, inputs, outputs, constraints, done signal) → cloud agent works on a `cursor/*` branch → PR → **Kieran reviews and merges** → Kieran deploys if needed → Grok Bot updates AGENTS.md + vault status.

**Hard rules**
- Nothing goes to prospects without Kieran's explicit OK.
- Agents never deploy, change DNS, or send prospect email.
- Prospect lists, report output and `wave*-links.csv` stay in the vault, never in git.
- Wave-2 audience: Ltd/LLP firms only (PECR).
