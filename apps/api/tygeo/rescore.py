"""Recompute probe scores from stored response text (no new probe API calls)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from tygeo.analysis import aggregate_composite_score, analyze_response
from tygeo.models import QueryResult, Recommendation, Run


@dataclass(frozen=True)
class RescoreStats:
    mentions_before: int
    mentions_after: int
    visibility_before: float
    visibility_after: float
    composite_before: float
    composite_after: float

    @property
    def changed(self) -> bool:
        return (
            self.mentions_before != self.mentions_after
            or abs(self.visibility_before - self.visibility_after) > 1e-9
            or abs(self.composite_before - self.composite_after) > 1e-9
        )


def _brand_context_from_run(run: Run | dict[str, Any]) -> tuple[str, list[str], list[str]]:
    if isinstance(run, dict):
        snap = run.get("profile_snapshot") or {}
        brand = str(run.get("brand_name") or snap.get("brand_name") or "").strip()
        aliases = [str(a) for a in (snap.get("aliases") or []) if str(a).strip()]
        competitors = [str(c) for c in (snap.get("competitors") or []) if str(c).strip()]
        return brand, aliases, competitors
    snap = run.profile_snapshot or {}
    brand = str(run.brand_name or snap.get("brand_name") or "").strip()
    aliases = [str(a) for a in (snap.get("aliases") or []) if str(a).strip()]
    competitors = [str(c) for c in (snap.get("competitors") or []) if str(c).strip()]
    return brand, aliases, competitors


def _row_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    return {
        "response_text": row.response_text,
        "brand_mentioned": row.brand_mentioned,
        "competitors_mentioned": row.competitors_mentioned,
        "sentiment": row.sentiment,
        "mention_position": row.mention_position,
        "relevance_score": row.relevance_score,
        "cited_domains": row.cited_domains,
        "query_text": row.query_text,
    }


def preview_rescore_run(run: Run | dict[str, Any]) -> RescoreStats:
    """Compute before/after stats without mutating storage."""
    brand, aliases, competitors = _brand_context_from_run(run)
    rows = (
        list(run.get("query_results") or [])
        if isinstance(run, dict)
        else list(run.query_results or [])
    )
    if not rows:
        return RescoreStats(0, 0, 0.0, 0.0, 0.0, 0.0)

    before_results: list[dict[str, Any]] = []
    after_results: list[dict[str, Any]] = []
    mentions_before = 0
    mentions_after = 0

    for raw in rows:
        row = _row_dict(raw)
        prev_hit = bool(row.get("brand_mentioned"))
        if prev_hit:
            mentions_before += 1
        text = str(row.get("response_text") or "")
        brand_hit, comp = analyze_response(
            text,
            brand=brand,
            competitors=competitors,
            aliases=aliases,
        )
        if brand_hit:
            mentions_after += 1
        sentiment = str(row.get("sentiment") or "neutral")
        position = str(row.get("mention_position") or "not_mentioned")
        relevance = float(row.get("relevance_score") or 0.0)
        if brand_hit and not prev_hit:
            sentiment, position, relevance = "neutral", "secondary", 0.5
        elif not brand_hit:
            sentiment, position, relevance = "neutral", "not_mentioned", 0.0

        before_results.append(
            {
                "brand_mentioned": prev_hit,
                "mention_position": row.get("mention_position"),
                "sentiment": row.get("sentiment"),
                "cited_domains": row.get("cited_domains"),
            }
        )
        after_results.append(
            {
                "brand_mentioned": brand_hit,
                "mention_position": position,
                "sentiment": sentiment,
                "cited_domains": row.get("cited_domains"),
                "competitors_mentioned": comp,
            }
        )

    n = len(rows)
    vis_before = mentions_before / n
    vis_after = mentions_after / n
    comp_before = aggregate_composite_score(before_results)
    comp_after = aggregate_composite_score(after_results)
    return RescoreStats(
        mentions_before=mentions_before,
        mentions_after=mentions_after,
        visibility_before=vis_before,
        visibility_after=vis_after,
        composite_before=comp_before,
        composite_after=comp_after,
    )


def rescore_run(db: Session, run: Run) -> RescoreStats:
    """Update query rows and run aggregates from stored response_text (no LLM)."""
    if run.status != "completed":
        raise ValueError(f"Run {run.id} is not completed (status={run.status})")

    stats = preview_rescore_run(run)
    brand, aliases, competitors = _brand_context_from_run(run)

    for qr in run.query_results:
        prev_hit = bool(qr.brand_mentioned)
        text = qr.response_text or ""
        brand_hit, comp = analyze_response(
            text,
            brand=brand,
            competitors=competitors,
            aliases=aliases,
        )
        qr.brand_mentioned = brand_hit
        qr.competitors_mentioned = comp
        if brand_hit and not prev_hit:
            qr.sentiment = "neutral"
            qr.mention_position = "secondary"
            qr.relevance_score = 0.5
        elif not brand_hit:
            qr.sentiment = "neutral"
            qr.mention_position = "not_mentioned"
            qr.relevance_score = 0.0

    result_rows = [
        {
            "brand_mentioned": qr.brand_mentioned,
            "mention_position": qr.mention_position,
            "sentiment": qr.sentiment,
            "cited_domains": qr.cited_domains,
        }
        for qr in run.query_results
    ]
    n = len(result_rows) or 1
    run.visibility_rate = sum(1 for r in result_rows if r["brand_mentioned"]) / n
    run.composite_score = aggregate_composite_score(result_rows)

    # Recommendations were generated from prior aggregates; drop without re-calling LLM.
    for rec in list(run.recommendations or []):
        db.delete(rec)

    db.commit()
    db.refresh(run)
    return stats
