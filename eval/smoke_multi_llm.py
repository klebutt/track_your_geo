"""Live smoke test: one probe per enabled model. Run from repo root."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))

from tygeo.citations import build_cited_domains  # noqa: E402
from tygeo.config import Settings  # noqa: E402
from tygeo.llm import run_geo_query_provider  # noqa: E402

PROMPT = "What are the best Indian restaurants in London? Name specific venues."
LOCATION = "London, UK"
BRAND = "Dishoom"
BRAND_DOMAINS = ["dishoom.com"]


def main() -> int:
    settings = Settings()
    models = settings.enabled_probe_models
    print(f"Enabled probe models ({len(models)}): {', '.join(models)}")

    missing: list[str] = []
    if not settings.openai_api_key:
        missing.append("OPENAI_API_KEY")
    if any(m.startswith("perplexity/") for m in models) and not settings.perplexity_api_key:
        missing.append("PERPLEXITY_API_KEY")
    if any(m.startswith("gemini/") for m in models) and not settings.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if missing:
        print(f"ERROR: missing keys: {', '.join(missing)}")
        return 1

    total_cost = 0.0
    ok = 0
    for model in models:
        print(f"\n--- {model} ---")
        try:
            text, meta, annotations, citation_urls, gemini_response = run_geo_query_provider(
                settings,
                model,
                PROMPT,
                location=LOCATION,
            )
        except Exception as exc:
            print(f"FAIL: {exc}")
            continue

        cited = build_cited_domains(
            text,
            annotations,
            brand_name=BRAND,
            brand_domains=BRAND_DOMAINS,
            model_name=model,
            citation_urls=citation_urls,
            gemini_response=gemini_response,
        )
        domains = [c["domain"] for c in cited]
        cost = meta.get("cost_usd", 0.0)
        total_cost += cost
        ok += 1
        print(f"probe_path: {meta.get('probe_path')}")
        print(f"latency_ms: {meta.get('latency_ms', 0):.0f}")
        print(f"cost_usd: {cost:.5f}")
        print(f"cited_domains ({len(domains)}): {domains[:8]}")
        print(f"response_preview: {text[:200].replace(chr(10), ' ')}...")

    print(f"\nSummary: {ok}/{len(models)} models succeeded, total_cost=${total_cost:.4f}")
    return 0 if ok == len(models) else 1


if __name__ == "__main__":
    raise SystemExit(main())
