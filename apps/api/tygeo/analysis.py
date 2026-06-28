from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from tygeo.citations import build_cited_domains
from tygeo.config import Settings
from tygeo.llm import run_geo_query_provider
from tygeo.models import QueryResult, Run
from tygeo.pilots import PilotProfile

logger = logging.getLogger(__name__)


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


def _models_with_credentials(settings: Settings, models: list[str]) -> list[str]:
    ready: list[str] = []
    for model in models:
        if model.startswith("perplexity/") and not settings.perplexity_api_key:
            logger.warning("Skipping %s: PERPLEXITY_API_KEY not set", model)
            continue
        if model.startswith("gemini/") and not settings.gemini_api_key:
            logger.warning("Skipping %s: GEMINI_API_KEY not set", model)
            continue
        if not settings.openai_api_key and not model.startswith(("perplexity/", "gemini/")):
            logger.warning("Skipping %s: OPENAI_API_KEY not set", model)
            continue
        ready.append(model)
    return ready


def create_pending_run(
    db: Session,
    settings: Settings,
    pilot: PilotProfile,
    *,
    brand_override: str | None,
    location_override: str | None,
) -> Run:
    brand = brand_override or pilot.brand_name
    location = location_override or pilot.location
    enabled_models = _models_with_credentials(settings, settings.enabled_probe_models)
    if not enabled_models:
        raise ValueError("No probe models available: check API keys and TYGEO_ENABLED_PROBES")
    run = Run(
        pilot_id=pilot.id,
        brand_name=brand,
        location=location,
        model_name=",".join(enabled_models),
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def execute_run(
    db: Session,
    settings: Settings,
    pilot: PilotProfile,
    *,
    brand_override: str | None,
    location_override: str | None,
    run: Run | None = None,
) -> Run:
    brand = brand_override or pilot.brand_name
    location = location_override or pilot.location

    usage_log: list[dict] = []
    total_cost = 0.0
    total_pt = 0
    total_ct = 0

    enabled_models = _models_with_credentials(settings, settings.enabled_probe_models)
    if not enabled_models:
        raise ValueError("No probe models available: check API keys and TYGEO_ENABLED_PROBES")

    if run is None:
        run = Run(
            pilot_id=pilot.id,
            brand_name=brand,
            location=location,
            model_name=",".join(enabled_models),
            status="running",
        )
        db.add(run)
        db.flush()
    else:
        brand = run.brand_name
        location = run.location

    results: list[tuple[str, str, bool, dict[str, bool], dict]] = []

    for q_template in pilot.queries:
        q = pilot.format_query(q_template, brand=brand, location=location)
        for model in enabled_models:
            try:
                text, meta, annotations, citation_urls, gemini_response = run_geo_query_provider(
                    settings,
                    model,
                    q,
                    location=location,
                )
            except Exception as exc:
                logger.exception("Probe failed for model=%s query=%r", model, q)
                usage_log.append(
                    {
                        "phase": "probe_error",
                        "query": q,
                        "model": model,
                        "error": str(exc),
                    }
                )
                db.commit()
                continue

            usage_log.append({"phase": "probe", "query": q, **meta})
            cost_usd = float(meta.get("cost_usd") or 0.0)
            total_cost += cost_usd
            total_pt += int(meta.get("prompt_tokens") or 0)
            total_ct += int(meta.get("completion_tokens") or 0)

            brand_hit, comp = analyze_response(text, brand=brand, competitors=pilot.competitors)
            cited = build_cited_domains(
                text,
                annotations,
                brand_name=brand,
                brand_domains=pilot.brand_domains,
                model_name=model,
                citation_urls=citation_urls,
                gemini_response=gemini_response,
            )
            qr = QueryResult(
                run_id=run.id,
                query_text=q,
                response_text=text,
                brand_mentioned=brand_hit,
                competitors_mentioned=comp,
                cited_domains=cited,
                model_name=model,
                latency_ms=float(meta.get("latency_ms") or 0.0),
                cost_usd=cost_usd,
                prompt_tokens=int(meta.get("prompt_tokens") or 0),
                completion_tokens=int(meta.get("completion_tokens") or 0),
            )
            db.add(qr)
            results.append((q, text, brand_hit, comp, meta))
            db.commit()

    if not results:
        run.status = "failed"
        run.usage_log = usage_log or None
        db.commit()
        raise RuntimeError("All probes failed — check API keys, quotas, and Railway logs.")

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


def finish_run_probes(
    run_id: int,
    pilot_id: str,
    *,
    brand_override: str | None,
    location_override: str | None,
) -> None:
    """Background worker: load pilot and execute probes for a pending run."""
    from tygeo.config import Settings as SettingsCls
    from tygeo.db import new_session
    from tygeo.pilots import load_pilot

    settings = SettingsCls()
    db = new_session()
    try:
        pilot = load_pilot(settings.pilot_dir_path, pilot_id)
        run = db.query(Run).filter(Run.id == run_id).first()
        if not pilot or not run:
            if run:
                run.status = "failed"
                db.commit()
            return
        execute_run(
            db,
            settings,
            pilot,
            brand_override=brand_override,
            location_override=location_override,
            run=run,
        )
    except Exception:
        logger.exception("Background run %s failed", run_id)
        db.rollback()
        run = db.query(Run).filter(Run.id == run_id).first()
        if run and run.status == "running":
            run.status = "failed"
            db.commit()
    finally:
        db.close()
