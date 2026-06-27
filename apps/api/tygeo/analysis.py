from __future__ import annotations

from sqlalchemy.orm import Session

from tygeo.citations import build_cited_domains
from tygeo.config import Settings
from tygeo.llm import run_geo_query
from tygeo.models import QueryResult, Run
from tygeo.pilots import PilotProfile


def _mentions(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def analyze_response(
    response_text: str,
    *,
    brand: str,
    competitors: list[str],
) -> tuple[bool, dict[str, bool]]:
    brand_hit = _mentions(response_text, brand)
    comp: dict[str, bool] = {}
    for c in competitors:
        comp[c] = _mentions(response_text, c)
    return brand_hit, comp


def composite_score(visibility_rate: float, brand_mentions: int, total: int) -> float:
    """v0.1: visibility dominates; small bump if majority of answers mention brand."""
    if total <= 0:
        return 0.0
    base = visibility_rate * 100.0
    bonus = min(10.0, (brand_mentions / total) * 10.0)
    return round(min(100.0, base * 0.85 + bonus), 2)


def execute_run(
    db: Session,
    settings: Settings,
    pilot: PilotProfile,
    *,
    brand_override: str | None,
    location_override: str | None,
) -> Run:
    brand = brand_override or pilot.brand_name
    location = location_override or pilot.location

    usage_log: list[dict] = []
    total_cost = 0.0
    total_pt = 0
    total_ct = 0

    run = Run(
        pilot_id=pilot.id,
        brand_name=brand,
        location=location,
        model_name=settings.tygeo_probe_model,
        status="running",
    )
    db.add(run)
    db.flush()

    results: list[tuple[str, str, bool, dict[str, bool], dict]] = []

    for q_template in pilot.queries:
        q = pilot.format_query(q_template, brand=brand, location=location)
        text, meta, annotations = run_geo_query(settings, q, location=location)
        usage_log.append({"phase": "probe", "query": q, **meta})
        total_cost += meta["cost_usd"]
        total_pt += meta["prompt_tokens"]
        total_ct += meta["completion_tokens"]

        brand_hit, comp = analyze_response(text, brand=brand, competitors=pilot.competitors)
        cited = build_cited_domains(
            text,
            annotations,
            brand_name=brand,
            brand_domains=pilot.brand_domains,
        )
        qr = QueryResult(
            run_id=run.id,
            query_text=q,
            response_text=text,
            brand_mentioned=brand_hit,
            competitors_mentioned=comp,
            cited_domains=cited,
            latency_ms=meta["latency_ms"],
            cost_usd=meta["cost_usd"],
            prompt_tokens=meta["prompt_tokens"],
            completion_tokens=meta["completion_tokens"],
        )
        db.add(qr)
        results.append((q, text, brand_hit, comp, meta))

    n = len(results)
    vis = sum(1 for _, _, hit, _, _ in results if hit) / n if n else 0.0
    brand_mentions = sum(1 for _, _, hit, _, _ in results if hit)

    run.status = "completed"
    run.total_cost_usd = total_cost
    run.total_prompt_tokens = total_pt
    run.total_completion_tokens = total_ct
    run.visibility_rate = vis
    run.composite_score = composite_score(vis, brand_mentions, n)
    run.usage_log = usage_log

    db.commit()
    db.refresh(run)
    return run
