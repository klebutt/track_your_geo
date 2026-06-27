# Proposal: local MVP prototype (journeys 1, 2, 4)

## Why

We need a credible **working demo** that shows how Track Your GEO will probe generative answers, quantify brand visibility for a pilot profile, surface gaps, and suggest prioritized actions—without building onboarding, time series, or exports yet.

## What

- YAML-driven **pilot profiles** (brand, geography, competitors, query bank, optional seed domains).
- **FastAPI** backend calling models through **LiteLLM**, persisting runs to **SQLite**, exposing REST for the UI.
- **Vite + React** dashboard: pick pilot, optional overrides, run batch probes, view visibility, per-query table, and recommendations with **run cost** surfaced.
- **DeepEval** in-repo tests for golden substring checks (extensible to LLM-as-judge later).
- **OpenSpec** as the durable requirements layer for iterations.

## Out of scope (this change)

- Auth, multi-tenant billing, scheduled monitoring, PDF exports.
- Perfect parity with consumer ChatGPT/Claude UIs or regional browsing behavior.

## Success criteria

- A stakeholder can complete journeys **1 → 2 → 4** locally using one pilot file and see defensible, repeatable outputs plus approximate LLM cost.
