from __future__ import annotations

import json
import re
import time
from typing import Any

import litellm
from litellm import completion_cost

from tygeo.config import Settings


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try:
            data = json.loads(m.group())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return []


def _usage_tokens(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    pt = getattr(usage, "prompt_tokens", None) if usage else None
    ct = getattr(usage, "completion_tokens", None) if usage else None
    if pt is None and usage and isinstance(usage, dict):
        pt = usage.get("prompt_tokens", 0)
        ct = usage.get("completion_tokens", 0)
    if pt is None:
        pt = 0
    if ct is None:
        ct = 0
    return int(pt), int(ct)


def complete(
    settings: Settings,
    messages: list[dict[str, str]],
    temperature: float = 0.3,
) -> tuple[str, dict[str, Any]]:
    """Returns assistant text and metadata (tokens, cost, latency)."""
    if settings.openai_api_key:
        litellm.api_key = settings.openai_api_key

    t0 = time.perf_counter()
    response = litellm.completion(
        model=settings.tygeo_model,
        messages=messages,
        temperature=temperature,
    )
    latency_ms = (time.perf_counter() - t0) * 1000

    choice = response.choices[0]
    text = choice.message.content or ""
    pt, ct = _usage_tokens(response)

    try:
        cost = float(completion_cost(completion_response=response))
    except Exception:
        cost = 0.0

    meta = {
        "model": settings.tygeo_model,
        "latency_ms": latency_ms,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "cost_usd": cost,
    }
    return text, meta


def run_geo_query(
    settings: Settings,
    user_prompt: str,
    *,
    location: str | None = None,
) -> tuple[str, dict[str, Any], list[Any]]:
    """GEO probe via OpenAI search model; returns text, metadata, and url_citation annotations."""
    if settings.openai_api_key:
        litellm.api_key = settings.openai_api_key

    system = (
        "You are answering as a general knowledge assistant with web search. "
        "Answer naturally for the user's location when relevant. "
        "List specific venues or products by name when asked."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]

    web_search_options: dict[str, Any] = {
        "search_context_size": settings.tygeo_search_context_size,
    }
    if location:
        web_search_options["user_location"] = {
            "type": "approximate",
            "approximate": {"region": location},
        }

    t0 = time.perf_counter()
    response = litellm.completion(
        model=settings.tygeo_probe_model,
        messages=messages,
        web_search_options=web_search_options,
    )
    latency_ms = (time.perf_counter() - t0) * 1000

    choice = response.choices[0]
    text = choice.message.content or ""
    annotations = getattr(choice.message, "annotations", None) or []
    pt, ct = _usage_tokens(response)

    try:
        cost = float(completion_cost(completion_response=response))
    except Exception:
        cost = 0.0

    meta = {
        "model": settings.tygeo_probe_model,
        "probe_path": "web_search",
        "latency_ms": latency_ms,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "cost_usd": cost,
    }
    return text, meta, list(annotations)


def run_recommendations(
    settings: Settings,
    *,
    brand: str,
    location: str,
    visibility_rate: float,
    missing_queries: list[str],
    competitor_wins: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    user = json.dumps(
        {
            "brand": brand,
            "location": location,
            "visibility_rate": visibility_rate,
            "queries_where_brand_missing_or_weak": missing_queries[:25],
            "competitors_often_listed": competitor_wins[:15],
            "task": (
                "Return a JSON array only (no markdown), each item: "
                '{"title": str, "detail": str, "impact": "high"|"medium"|"low", '
                '"category": "website"|"third_party"|"pr_comms"|"other"}'
            ),
        },
        ensure_ascii=False,
    )
    messages = [
        {
            "role": "system",
            "content": "You advise brands on Generative Engine Optimization (GEO). Be practical.",
        },
        {"role": "user", "content": user},
    ]
    text, meta = complete(settings, messages, temperature=0.4)
    items = _extract_json_array(text)
    cleaned: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        title = str(it.get("title", "")).strip()
        if not title:
            continue
        cleaned.append(
            {
                "title": title,
                "detail": str(it.get("detail", "")).strip(),
                "impact": str(it.get("impact", "medium")).lower(),
                "category": str(it.get("category", "other")).lower(),
            }
        )
    return cleaned, meta
