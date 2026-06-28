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


def _set_provider_api_key(settings: Settings, model: str) -> None:
    if model.startswith("perplexity/"):
        if settings.perplexity_api_key:
            litellm.api_key = settings.perplexity_api_key
        return
    if model.startswith("gemini/"):
        if settings.gemini_api_key:
            litellm.api_key = settings.gemini_api_key
        return
    if settings.openai_api_key:
        litellm.api_key = settings.openai_api_key


def _probe_messages(user_prompt: str) -> list[dict[str, str]]:
    system = (
        "You are answering as a general knowledge assistant with web search. "
        "Answer naturally for the user's location when relevant. "
        "List specific venues or products by name when asked."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]


def _completion_meta(response: Any, *, model: str, probe_path: str, t0: float) -> dict[str, Any]:
    latency_ms = (time.perf_counter() - t0) * 1000
    pt, ct = _usage_tokens(response)
    try:
        cost = float(completion_cost(completion_response=response))
    except Exception:
        cost = 0.0
    return {
        "model": model,
        "probe_path": probe_path,
        "latency_ms": latency_ms,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "cost_usd": cost,
    }


def run_geo_query_provider(
    settings: Settings,
    model: str,
    user_prompt: str,
    *,
    location: str | None = None,
) -> tuple[str, dict[str, Any], list[Any], list[str], Any | None]:
    """GEO probe for a single provider model.

    Returns text, metadata, annotations, perplexity citation URLs, and raw response
    (for Gemini grounding extraction).
    """
    _set_provider_api_key(settings, model)
    messages = _probe_messages(user_prompt)
    t0 = time.perf_counter()

    if model.startswith("gemini/"):
        response = litellm.completion(
            model=model,
            messages=messages,
            tools=[{"googleSearch": {}}],
        )
        choice = response.choices[0]
        text = choice.message.content or ""
        annotations = getattr(choice.message, "annotations", None) or []
        meta = _completion_meta(response, model=model, probe_path="google_search", t0=t0)
        return text, meta, list(annotations), [], response

    if model.startswith("perplexity/"):
        response = litellm.completion(model=model, messages=messages)
        choice = response.choices[0]
        text = choice.message.content or ""
        annotations = getattr(choice.message, "annotations", None) or []
        citation_urls = list(getattr(response, "citations", None) or [])
        if not citation_urls:
            search_results = getattr(response, "search_results", None) or []
            for item in search_results:
                if isinstance(item, dict):
                    url = item.get("url")
                else:
                    url = getattr(item, "url", None)
                if url:
                    citation_urls.append(url)
        meta = _completion_meta(response, model=model, probe_path="perplexity_citations", t0=t0)
        return text, meta, list(annotations), citation_urls, None

    web_search_options: dict[str, Any] = {
        "search_context_size": settings.tygeo_search_context_size,
    }
    if location:
        web_search_options["user_location"] = {
            "type": "approximate",
            "approximate": {"region": location},
        }

    response = litellm.completion(
        model=model,
        messages=messages,
        web_search_options=web_search_options,
    )
    choice = response.choices[0]
    text = choice.message.content or ""
    annotations = getattr(choice.message, "annotations", None) or []
    meta = _completion_meta(response, model=model, probe_path="web_search", t0=t0)
    return text, meta, list(annotations), [], None


def run_geo_query(
    settings: Settings,
    user_prompt: str,
    *,
    location: str | None = None,
    model: str | None = None,
) -> tuple[str, dict[str, Any], list[Any]]:
    """Backward-compatible wrapper around the default probe model."""
    probe_model = model or settings.tygeo_probe_model
    text, meta, annotations, _urls, _response = run_geo_query_provider(
        settings,
        probe_model,
        user_prompt,
        location=location,
    )
    return text, meta, annotations


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
