from __future__ import annotations

import re
from typing import Any, Literal
from urllib.parse import urlparse

CitationKind = Literal["brand_owned", "third_party"]

_HTTP_URL_RE = re.compile(r"https?://[^\s\)\]>\"']+", re.IGNORECASE)
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\((https?://[^)]+)\)", re.IGNORECASE)


def normalize_domain(domain: str) -> str:
    d = domain.lower().strip().rstrip(".")
    if d.startswith("www."):
        return d[4:]
    return d


def _domain_from_url(url: str) -> str | None:
    raw = url.strip().rstrip(".,;:)")
    if not raw:
        return None
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = parsed.netloc or ""
    if not host and parsed.path:
        host = parsed.path.split("/")[0]
    if not host or "." not in host:
        return None
    return normalize_domain(host)


def _brand_slug(brand_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", brand_name.lower())


def is_brand_owned(domain: str, *, brand_name: str, brand_domains: list[str]) -> bool:
    normalized = normalize_domain(domain)
    configured = {normalize_domain(d) for d in brand_domains if d.strip()}
    if normalized in configured:
        return True
    slug = _brand_slug(brand_name)
    if len(slug) >= 4 and slug in normalized:
        return True
    return False


def extract_domains(text: str) -> list[str]:
    """Return deduplicated domains in first-seen order from URLs in text."""
    hits: list[tuple[int, str]] = []

    for match in _MARKDOWN_LINK_RE.finditer(text):
        domain = _domain_from_url(match.group(1))
        if domain:
            hits.append((match.start(), domain))

    for match in _HTTP_URL_RE.finditer(text):
        domain = _domain_from_url(match.group(0))
        if domain:
            hits.append((match.start(), domain))

    hits.sort(key=lambda item: item[0])
    ordered: list[str] = []
    seen: set[str] = set()
    for _, domain in hits:
        if domain not in seen:
            seen.add(domain)
            ordered.append(domain)
    return ordered


def _annotation_url(annotation: object) -> str | None:
    if isinstance(annotation, dict):
        if annotation.get("type") != "url_citation":
            return None
        citation = annotation.get("url_citation") or {}
        return citation.get("url") if isinstance(citation, dict) else None
    citation = getattr(annotation, "url_citation", None)
    if citation is None:
        return None
    return getattr(citation, "url", None)


def extract_domains_from_list(urls: list[str]) -> list[str]:
    """Domains from Perplexity's top-level citations URL array."""
    ordered: list[str] = []
    seen: set[str] = set()
    for url in urls:
        domain = _domain_from_url(url)
        if domain and domain not in seen:
            seen.add(domain)
            ordered.append(domain)
    return ordered


def _gemini_chunk_url(chunk: object) -> str | None:
    if isinstance(chunk, dict):
        web = chunk.get("web") or {}
        if isinstance(web, dict):
            return web.get("uri") or web.get("url")
        return None
    web = getattr(chunk, "web", None)
    if web is None:
        return None
    return getattr(web, "uri", None) or getattr(web, "url", None)


def extract_domains_from_gemini(response_obj: Any) -> list[str]:
    """Domains from Gemini grounding metadata or LiteLLM-mapped annotations."""
    ordered: list[str] = []
    seen: set[str] = set()

    def add_url(url: str | None) -> None:
        if not url:
            return
        domain = _domain_from_url(url)
        if domain and domain not in seen:
            seen.add(domain)
            ordered.append(domain)

    grounding = getattr(response_obj, "grounding_metadata", None)
    if grounding is None and hasattr(response_obj, "candidates"):
        candidates = getattr(response_obj, "candidates", None) or []
        if candidates:
            grounding = getattr(candidates[0], "grounding_metadata", None)

    if grounding is not None:
        chunks = getattr(grounding, "grounding_chunks", None)
        if chunks is None and isinstance(grounding, dict):
            chunks = grounding.get("grounding_chunks")
        for chunk in chunks or []:
            add_url(_gemini_chunk_url(chunk))

    provider_fields = getattr(response_obj, "provider_specific_fields", None) or {}
    if isinstance(provider_fields, dict):
        vertex_grounding = provider_fields.get("vertex_ai_grounding_metadata") or {}
        if isinstance(vertex_grounding, dict):
            for chunk in vertex_grounding.get("grounding_chunks") or []:
                if isinstance(chunk, dict):
                    web = chunk.get("web") or {}
                    if isinstance(web, dict):
                        add_url(web.get("uri") or web.get("url"))

    choices = getattr(response_obj, "choices", None) or []
    if choices:
        message = getattr(choices[0], "message", None)
        annotations = getattr(message, "annotations", None) if message else None
        for domain in extract_domains_from_annotations(list(annotations or [])):
            if domain not in seen:
                seen.add(domain)
                ordered.append(domain)

    return ordered


def extract_domains_from_annotations(annotations: list[object]) -> list[str]:
    """Domains from OpenAI search-model url_citation annotations (provider-grounded)."""
    ordered: list[str] = []
    seen: set[str] = set()
    for annotation in annotations:
        url = _annotation_url(annotation)
        if not url:
            continue
        domain = _domain_from_url(url)
        if domain and domain not in seen:
            seen.add(domain)
            ordered.append(domain)
    return ordered


def _classify_domain_list(
    domains: list[str],
    *,
    brand_name: str,
    brand_domains: list[str],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for domain in domains:
        kind: CitationKind = (
            "brand_owned"
            if is_brand_owned(domain, brand_name=brand_name, brand_domains=brand_domains)
            else "third_party"
        )
        result.append({"domain": domain, "kind": kind})
    return result


def classify_cited_domains(
    text: str,
    *,
    brand_name: str,
    brand_domains: list[str],
) -> list[dict[str, str]]:
    return _classify_domain_list(
        extract_domains(text),
        brand_name=brand_name,
        brand_domains=brand_domains,
    )


def build_cited_domains(
    text: str,
    annotations: list[object] | None,
    *,
    brand_name: str,
    brand_domains: list[str],
    model_name: str | None = None,
    citation_urls: list[str] | None = None,
    gemini_response: Any | None = None,
) -> list[dict[str, str]]:
    """Prefer provider-grounded citations; fall back to URL parsing in reply text."""
    provider_domains: list[str] = []
    if model_name and model_name.startswith("perplexity/"):
        provider_domains = extract_domains_from_list(citation_urls or [])
        if not provider_domains:
            provider_domains = extract_domains_from_annotations(annotations or [])
    elif model_name and model_name.startswith("gemini/"):
        provider_domains = extract_domains_from_gemini(gemini_response or annotations)
        if not provider_domains:
            provider_domains = extract_domains_from_annotations(annotations or [])
    else:
        provider_domains = extract_domains_from_annotations(annotations or [])

    from_text = extract_domains(text)
    combined: list[str] = []
    seen: set[str] = set()
    for domain in provider_domains + from_text:
        if domain not in seen:
            seen.add(domain)
            combined.append(domain)
    return _classify_domain_list(
        combined,
        brand_name=brand_name,
        brand_domains=brand_domains,
    )
