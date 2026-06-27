# Design: MVP prototype

## Architecture

- **Monorepo**: Python package `tygeo` under `apps/api/`, static SPA under `apps/web/`.
- **LLM**: LiteLLM `completion` with model from `TYGEO_MODEL` (default `gpt-4o-mini`). Keys from `.env` (`OPENAI_API_KEY`).
- **Persistence**: SQLite file `data/tygeo.db` with `runs`, `query_results`, `recommendations`.
- **Mention detection (v0.1)**: Case-insensitive substring match for brand and each competitor name in the assistant text.
- **Scoring (v0.1)**: `composite_score` blends visibility rate with a small bonus for overall mention density (see `tygeo.analysis`).
- **Recommendations**: Second LLM call with structured JSON array; parsed leniently (extract first JSON array if model adds prose).

## API vs consumer GEO

The UI and OpenSpec specs must state clearly that **API completions are not identical** to end-user chat experiences (tools, browsing, regional routing).

## Risks / follow-ups

- Hallucinated brand mentions: future pass with a lightweight judge or entity extraction.
- Source extraction: when models omit URLs, show pilot `seed_domains` as illustrative only (labeled in UI).
