from __future__ import annotations

import re
from typing import Literal
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
) -> list[dict[str, str]]:
    """Prefer search annotations; fall back to URL parsing in reply text."""
    from_annotations = extract_domains_from_annotations(annotations or [])
    from_text = extract_domains(text)
    combined: list[str] = []
    seen: set[str] = set()
    for domain in from_annotations + from_text:
        if domain not in seen:
            seen.add(domain)
            combined.append(domain)
    return _classify_domain_list(
        combined,
        brand_name=brand_name,
        brand_domains=brand_domains,
    )
