# Worklog — 2026-09-12 (OpenAI search migrate)

## Problem

`gpt-4o-mini-search-preview` shut down 2026-07-23. Every OpenAI probe returned 404; runs effectively used only Perplexity + Gemini.

## Fix (Path A)

Keep Chat Completions + `web_search_options`; swap model to **`gpt-5-search-api`** (OpenAI’s Chat Completions search successor). Outreach stays on **3 models** (OpenAI + Perplexity + Gemini).

## Changed

- Defaults: `apps/api/tygeo/config.py`
- Local `.env`, `.env.example`
- README Railway env table; `openspec/specs/geo-probe/spec.md`
- Eval fixtures/monkeypatches referencing the old model id

## Validation

- `pytest eval -q` → **57 passed**
- Live single probe `gpt-5-search-api`: `probe_path=web_search`, ~$0.05, 3 `url_citation` annotations — OK

## You still need to do

Update **Railway** env (prod will keep 404s until this is set):

```text
TYGEO_ENABLED_PROBES=gpt-5-search-api,perplexity/sonar-pro,gemini/gemini-2.5-flash
TYGEO_PROBE_MODEL=gpt-5-search-api
```

Then redeploy/restart the Railway service. Commit + push of this repo change is separate when you’re ready.
