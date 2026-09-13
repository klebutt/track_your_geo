"""Deterministic plain-language report from stored probe rows (no LLM)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

EM_DASH = "\u2014"


def _no_em_dash(text: str) -> str:
    return text.replace(EM_DASH, " - ")


class LossEntry(BaseModel):
    query: str
    competitors: list[str] = Field(default_factory=list)


class DeeperInsight(BaseModel):
    title: str
    detail: str


class PlainReportOut(BaseModel):
    ready: bool = False
    searches_recommended: int = 0
    searches_total: int = 0
    headline: str = ""
    win_queries: list[str] = Field(default_factory=list)
    loss_queries: list[str] = Field(default_factory=list)
    loss_entries: list[LossEntry] = Field(default_factory=list)
    gap_summary: str | None = None
    models_note: str | None = None
    geography_note: str | None = None
    what_this_is: str | None = None
    meaning: str | None = None
    competitor_summary: str | None = None
    deeper_insights: list[DeeperInsight] = Field(default_factory=list)
    deeper_insights_lead: str | None = None
    index_note: str | None = None


# Sales-locked customer copy (£ is latin-1 U+00A3 - safe for Helvetica PDF).
DEEPER_INSIGHTS_LEAD = (
    "One-off options typically in the £5-20 range if you want to go further - "
    "reply if any of these would help."
)

INDEX_NOTE = (
    "Visibility = how often you appear in these replies. "
    "The composite index also reflects how strongly you are recommended, "
    "the tone when you are mentioned, and whether you are cited as a source - "
    "a compass, not a replica of consumer ChatGPT."
)

# Customer-facing model labels (never expose raw provider IDs in report copy).
MODEL_DISPLAY_NAMES: dict[str, str] = {
    "gpt-5-search-api": "OpenAI search",
    "perplexity/sonar-pro": "Perplexity",
    "gemini/gemini-2.5-flash": "Gemini",
}


def customer_model_labels(model_name: str) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for raw in (model_name or "").split(","):
        key = raw.strip()
        if not key:
            continue
        label = MODEL_DISPLAY_NAMES.get(key, key)
        # Drop path-like leftovers if an unknown raw ID slips through
        if "/" in label or label.startswith("gpt-") or "gemini-" in label:
            continue
        if label not in seen:
            seen.add(label)
            labels.append(label)
    return labels



def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _competitor_names(group: list[Any]) -> list[str]:
    names: set[str] = set()
    for r in group:
        comps = _row_get(r, "competitors_mentioned") or {}
        if not isinstance(comps, dict):
            continue
        for name, hit in comps.items():
            if hit and str(name).strip():
                names.add(str(name).strip())
    return sorted(names)


def _deeper_insights(*, brand_name: str) -> list[DeeperInsight]:
    brand = (brand_name or "").strip() or "your firm"
    return [
        DeeperInsight(
            title="See which AI models named whom - and the exact phrases used",
            detail=(
                "A deeper pass breaks down each search by model so you can see who was "
                "recommended, in what words, and where you were missing."
            ),
        ),
        DeeperInsight(
            title=f"Get a plain-English action plan for {brand}",
            detail=(
                "Prioritised next steps for your locality and services - what to change "
                "first so AI assistants are more likely to name you."
            ),
        ),
        DeeperInsight(
            title="Re-test after you update listings or pages",
            detail=(
                "Run the same customer-intent questions again after you make changes, "
                "and compare whether you appear more often."
            ),
        ),
    ]


def build_plain_report(
    *,
    status: str,
    brand_name: str,
    model_name: str = "",
    query_results: list[Any] | None = None,
    max_list: int = 5,
    locality_stance: str | None = None,
    location: str | None = None,
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
    loss_entries: list[LossEntry] = []
    brand_miss_no_comp = 0
    name_tally: Counter[str] = Counter()

    for query, group in by_query.items():
        brand_hit = any(bool(_row_get(r, "brand_mentioned")) for r in group)
        names = _competitor_names(group)
        if brand_hit:
            wins.append(query)
        elif names:
            loss_entries.append(LossEntry(query=query, competitors=names))
            for n in names:
                name_tally[n] += 1
        else:
            brand_miss_no_comp += 1

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
        gap_summary = (
            f"{brand} appeared in every search we asked - a strong signal for this set."
        )
    elif loss_entries:
        gap_summary = (
            f"{brand} showed up in some searches, but competitors appeared without them "
            "in others - those are the clearest places to improve."
        )
    else:
        gap_summary = (
            f"{brand} appeared in some searches but not others. "
            "Focus on the themes where they were missing."
        )

    top_names = [name for name, _ in name_tally.most_common(5)]
    if top_names:
        competitor_summary = (
            "Most often named instead: " + ", ".join(top_names) + "."
        )
    elif brand_miss_no_comp and x < n:
        competitor_summary = (
            "On the searches where you were missing, no tracked competitors were named "
            "in the AI replies we checked."
        )
    else:
        competitor_summary = None

    meaning = gap_summary

    what_this_is = (
        "We asked AI assistants who they would recommend for clients like yours, "
        "using brand-neutral customer questions - then checked whether your firm was named."
    )

    labels = customer_model_labels(model_name)
    if labels:
        models_note = (
            f"Each search was checked across {len(labels)} AI model"
            f"{'' if len(labels) == 1 else 's'} ({', '.join(labels)}). "
            "A search counts if any model mentioned the business."
        )
    else:
        models_note = (
            "A search counts if any model reply mentioned the business "
            "(multiple models may have been checked per question)."
        )

    geography_note = None
    if locality_stance:
        from tygeo.url_intake import geography_note_for_stance

        geography_note = geography_note_for_stance(
            locality_stance, primary_location=location or ""
        )
        if geography_note:
            geography_note = _no_em_dash(geography_note)

    capped_losses = loss_entries[:max_list]
    return PlainReportOut(
        ready=True,
        searches_recommended=x,
        searches_total=n,
        headline=headline,
        win_queries=wins[:max_list],
        loss_queries=[e.query for e in capped_losses],
        loss_entries=capped_losses,
        gap_summary=gap_summary,
        models_note=models_note,
        geography_note=geography_note,
        what_this_is=what_this_is,
        meaning=meaning,
        competitor_summary=competitor_summary,
        deeper_insights=_deeper_insights(brand_name=brand),
        deeper_insights_lead=DEEPER_INSIGHTS_LEAD,
        index_note=INDEX_NOTE,
    )
