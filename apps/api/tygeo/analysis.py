from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from tygeo.citations import build_cited_domains, normalize_domain
from tygeo.config import Settings
from tygeo.llm import extract_mention_details, run_geo_query_provider, run_recommendations
from tygeo.models import QueryResult, Recommendation, Run
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


def composite_score(
    *,
    brand_mentioned: bool,
    mention_position: str,
    sentiment: str,
    cited_domains: list | None,
) -> float:
    """Per-query GEO score on 0–100 scale."""
    return round(query_geo_score(
        brand_mentioned=brand_mentioned,
        mention_position=mention_position,
        sentiment=sentiment,
        cited_domains=cited_domains,
    ) * 100.0, 2)


def position_score(mention_position: str) -> float:
    return {"first_mentioned": 1.0, "secondary": 0.5}.get(mention_position, 0.0)


def sentiment_score(sentiment: str) -> float:
    return {"positive": 1.0, "neutral": 0.5, "negative": 0.0}.get(sentiment, 0.5)


def citation_score(cited_domains: list | None) -> float:
    n = len(cited_domains or [])
    return min(1.0, n / 5.0)


def query_geo_score(
    *,
    brand_mentioned: bool,
    mention_position: str,
    sentiment: str,
    cited_domains: list | None,
) -> float:
    visibility = 1.0 if brand_mentioned else 0.0
    return (
        0.40 * visibility
        + 0.30 * position_score(mention_position)
        + 0.20 * sentiment_score(sentiment)
        + 0.10 * citation_score(cited_domains)
    )


def compute_sentiment_summary(results: list[dict]) -> dict:
    """Breakdown of sentiment among probes where the brand was visible."""
    visible = [r for r in results if r["brand_mentioned"]]
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for row in visible:
        sentiment = row.get("sentiment", "neutral")
        if sentiment not in counts:
            sentiment = "neutral"
        counts[sentiment] += 1
    return {
        "counts": counts,
        "total_visible": len(visible),
        "total_probes": len(results),
    }


def compute_avg_position_score(results: list[dict]) -> float:
    visible = [r for r in results if r["brand_mentioned"]]
    if not visible:
        return 0.0
    total = sum(position_score(r["mention_position"]) for r in visible)
    return round(total / len(visible), 3)


def compute_citation_gaps(
    results: list[dict],
    *,
    brand_domains: list[str],
) -> list[dict]:
    """Third-party domains cited alongside competitors but not for the brand."""
    configured_brand = {normalize_domain(d) for d in brand_domains if d.strip()}
    brand_cited: set[str] = set()
    gap_counts: dict[str, int] = {}

    for row in results:
        cited = row.get("cited_domains") or []
        third_party: list[str] = []
        has_brand_owned = False
        for entry in cited:
            domain = entry.get("domain", "") if isinstance(entry, dict) else ""
            kind = entry.get("kind", "third_party") if isinstance(entry, dict) else "third_party"
            normalized = normalize_domain(domain)
            if kind == "brand_owned":
                has_brand_owned = True
                brand_cited.add(normalized)
            elif normalized:
                third_party.append(normalized)

        competitors_hit = any((row.get("competitors_mentioned") or {}).values())
        brand_weak = not row["brand_mentioned"] or not has_brand_owned
        if competitors_hit and brand_weak:
            for domain in third_party:
                if domain not in configured_brand and domain not in brand_cited:
                    gap_counts[domain] = gap_counts.get(domain, 0) + 1

    ranked = sorted(gap_counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"domain": domain, "count": count} for domain, count in ranked[:15]]


def _missing_or_weak_queries(results: list[dict]) -> list[str]:
    weak: list[str] = []
    for row in results:
        if not row["brand_mentioned"] or row["mention_position"] != "first_mentioned":
            weak.append(row["query_text"])
    return weak


def _competitor_wins(results: list[dict], competitors: list[str]) -> list[str]:
    wins = {name: 0 for name in competitors}
    for row in results:
        if row["brand_mentioned"] and row["mention_position"] == "first_mentioned":
            continue
        for name, mentioned in (row.get("competitors_mentioned") or {}).items():
            if mentioned and name in wins:
                wins[name] += 1
    ranked = sorted(wins.items(), key=lambda item: (-item[1], item[0]))
    return [name for name, count in ranked if count > 0][:15]


def aggregate_composite_score(rows: list[dict]) -> float:
    """Mean per-query GEO score on 0–100 scale."""
    if not rows:
        return 0.0
    total = sum(
        query_geo_score(
            brand_mentioned=row["brand_mentioned"],
            mention_position=row["mention_position"],
            sentiment=row["sentiment"],
            cited_domains=row.get("cited_domains"),
        )
        for row in rows
    )
    return round((total / len(rows)) * 100.0, 2)


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

    results: list[dict] = []

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

            if brand_hit:
                try:
                    extracted, ext_meta = extract_mention_details(settings, text, brand)
                    usage_log.append({"phase": "extraction", "query": q, **ext_meta})
                    ext_cost = float(ext_meta.get("cost_usd") or 0.0)
                    total_cost += ext_cost
                    total_pt += int(ext_meta.get("prompt_tokens") or 0)
                    total_ct += int(ext_meta.get("completion_tokens") or 0)
                    cost_usd += ext_cost
                    sentiment = extracted["sentiment"]
                    mention_position = extracted["position"]
                    relevance_score = extracted["relevance"]
                except Exception as exc:
                    logger.exception("Extraction failed for model=%s query=%r", model, q)
                    usage_log.append(
                        {
                            "phase": "extraction_error",
                            "query": q,
                            "model": model,
                            "error": str(exc),
                        }
                    )
                    sentiment = "neutral"
                    mention_position = "secondary"
                    relevance_score = 0.5
            else:
                sentiment = "neutral"
                mention_position = "not_mentioned"
                relevance_score = 0.0

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
                sentiment=sentiment,
                mention_position=mention_position,
                relevance_score=relevance_score,
            )
            db.add(qr)
            results.append(
                {
                    "query_text": q,
                    "brand_mentioned": brand_hit,
                    "mention_position": mention_position,
                    "sentiment": sentiment,
                    "cited_domains": cited,
                    "competitors_mentioned": comp,
                }
            )
            db.commit()

    if not results:
        run.status = "failed"
        run.usage_log = usage_log or None
        db.commit()
        raise RuntimeError("All probes failed — check API keys, quotas, and Railway logs.")

    n = len(results)
    vis = sum(1 for r in results if r["brand_mentioned"]) / n if n else 0.0

    run.status = "completed"
    run.total_cost_usd = total_cost
    run.total_prompt_tokens = total_pt
    run.total_completion_tokens = total_ct
    run.visibility_rate = vis
    run.composite_score = aggregate_composite_score(results)

    sentiment_summary = compute_sentiment_summary(results)
    avg_position = compute_avg_position_score(results)
    citation_gaps = compute_citation_gaps(results, brand_domains=pilot.brand_domains)
    missing_queries = _missing_or_weak_queries(results)
    competitor_wins = _competitor_wins(results, pilot.competitors)

    try:
        rec_items, rec_meta = run_recommendations(
            settings,
            brand=brand,
            location=location,
            visibility_rate=vis,
            composite_score=run.composite_score,
            sentiment_summary=sentiment_summary,
            avg_position=avg_position,
            citation_gaps=citation_gaps,
            missing_queries=missing_queries,
            competitor_wins=competitor_wins,
        )
        usage_log.append({"phase": "recommendations", **rec_meta})
        total_cost += float(rec_meta.get("cost_usd") or 0.0)
        total_pt += int(rec_meta.get("prompt_tokens") or 0)
        total_ct += int(rec_meta.get("completion_tokens") or 0)
        run.total_cost_usd = total_cost
        run.total_prompt_tokens = total_pt
        run.total_completion_tokens = total_ct
        for item in rec_items:
            db.add(
                Recommendation(
                    run_id=run.id,
                    title=item["title"],
                    detail=item["detail"],
                    impact=item["impact"],
                    category=item["category"],
                )
            )
    except Exception as exc:
        logger.exception("Recommendations failed for run %s", run.id)
        usage_log.append(
            {
                "phase": "recommendations_error",
                "error": str(exc),
            }
        )

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
