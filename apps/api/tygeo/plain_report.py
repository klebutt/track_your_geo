"""Deterministic plain-language report from stored probe rows (no LLM)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlainReportOut(BaseModel):
    ready: bool = False
    searches_recommended: int = 0
    searches_total: int = 0
    headline: str = ""
    win_queries: list[str] = Field(default_factory=list)
    loss_queries: list[str] = Field(default_factory=list)
    gap_summary: str | None = None
    models_note: str | None = None


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def build_plain_report(
    *,
    status: str,
    brand_name: str,
    model_name: str = "",
    query_results: list[Any] | None = None,
    max_list: int = 5,
) -> PlainReportOut:
    """Aggregate unique queries into an X/N recommend report.

    A search (unique query text) counts as recommended when any model reply
    mentioned the brand. Loss = competitor mentioned on at least one model and
    brand mentioned on none.
    """
    rows = list(query_results or [])
    if status != "completed" or not rows:
        return PlainReportOut(ready=False)

    by_query: dict[str, list[Any]] = {}
    for row in rows:
        q = str(_row_get(row, "query_text") or "").strip()
        if not q:
            continue
        by_query.setdefault(q, []).append(row)

    if not by_query:
        return PlainReportOut(ready=False)

    wins: list[str] = []
    losses: list[str] = []
    for query, group in by_query.items():
        brand_hit = any(bool(_row_get(r, "brand_mentioned")) for r in group)
        competitor_hit = False
        for r in group:
            comps = _row_get(r, "competitors_mentioned") or {}
            if isinstance(comps, dict) and any(bool(v) for v in comps.values()):
                competitor_hit = True
                break
        if brand_hit:
            wins.append(query)
        elif competitor_hit:
            losses.append(query)

    n = len(by_query)
    x = len(wins)
    brand = (brand_name or "Your business").strip() or "Your business"
    headline = f"AI assistants recommended {brand} in {x} of {n} searches"

    if x == 0:
        gap_summary = (
            f"{brand} did not appear in these AI searches. "
            "That is a clear visibility gap for the questions we asked."
        )
    elif x == n:
        gap_summary = f"{brand} appeared in every search we asked — a strong signal for this set."
    elif losses:
        gap_summary = (
            f"{brand} showed up in some searches, but competitors appeared without them "
            "in others — those are the clearest places to improve."
        )
    else:
        gap_summary = (
            f"{brand} appeared in some searches but not others. "
            "Focus on the themes where they were missing."
        )

    models = [m.strip() for m in (model_name or "").split(",") if m.strip()]
    if models:
        models_note = (
            f"Each search was checked across {len(models)} AI model"
            f"{'' if len(models) == 1 else 's'} ({', '.join(models)}). "
            "A search counts if any model mentioned the business."
        )
    else:
        models_note = (
            "A search counts if any model reply mentioned the business "
            "(multiple models may have been checked per question)."
        )

    return PlainReportOut(
        ready=True,
        searches_recommended=x,
        searches_total=n,
        headline=headline,
        win_queries=wins[:max_list],
        loss_queries=losses[:max_list],
        gap_summary=gap_summary,
        models_note=models_note,
    )
