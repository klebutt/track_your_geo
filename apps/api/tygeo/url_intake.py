from __future__ import annotations

import hashlib
import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import litellm
import yaml
from litellm import completion_cost

from tygeo.config import Settings
from tygeo.llm import EXTRACTION_MODEL, _extract_json_object, _parse_cost_usd, _usage_tokens
from tygeo.pilots import PilotProfile

logger = logging.getLogger(__name__)

SUPPORTED_VERTICALS = frozenset({"accountants"})
FETCH_TIMEOUT_S = 20.0
MAX_HTML_BYTES = 500_000
MAX_TEXT_CHARS = 12_000
MIN_USEFUL_TEXT = 200

_SUFFIX_RE = re.compile(
    r"\b(limited|ltd\.?|llp|llc|plc|inc\.?|co\.|company)\b",
    re.IGNORECASE,
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def get_text(self) -> str:
        return "\n".join(self._chunks)


def normalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("URL is required")
    if " " in raw or "\n" in raw:
        raise ValueError("URL must not contain whitespace")
    if not re.match(r"^https?://", raw, re.IGNORECASE):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be http(s) with a host")
    if "." not in parsed.netloc and parsed.netloc.lower() != "localhost":
        raise ValueError("URL host looks invalid")
    return raw


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        logger.exception("HTML parse failed; falling back to strip tags")
        return re.sub(r"<[^>]+>", " ", html)
    return parser.get_text()


def fetch_url_text(url: str) -> tuple[str, dict[str, Any]]:
    """Fetch URL and return plain text plus usage_log-style meta (no LLM cost)."""
    meta: dict[str, Any] = {"phase": "url_fetch", "url": url}
    try:
        with httpx.Client(
            timeout=FETCH_TIMEOUT_S,
            follow_redirects=True,
            headers={"User-Agent": "TrackYourGEO/0.1 (+https://track-your-geo.vercel.app)"},
        ) as client:
            resp = client.get(url)
            meta["status_code"] = resp.status_code
            resp.raise_for_status()
            raw = resp.content[:MAX_HTML_BYTES]
            ctype = (resp.headers.get("content-type") or "").lower()
            if "html" not in ctype and "text" not in ctype and ctype:
                meta["error"] = f"unsupported content-type: {ctype}"
                return "", meta
            text = html_to_text(raw.decode(resp.encoding or "utf-8", errors="replace"))
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            if len(text) > MAX_TEXT_CHARS:
                text = text[:MAX_TEXT_CHARS]
            meta["text_chars"] = len(text)
            return text, meta
    except Exception as exc:
        logger.warning("Fetch failed for %s: %s", url, exc)
        meta["error"] = str(exc)
        return "", meta


def _completion_cost_usd(response: Any) -> float:
    try:
        return _parse_cost_usd(completion_cost(completion_response=response))
    except Exception:
        return 0.0


def _llm_json(
    settings: Settings,
    *,
    system: str,
    user: str,
    phase: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if settings.openai_api_key:
        litellm.api_key = settings.openai_api_key
    import time

    t0 = time.perf_counter()
    response = litellm.completion(
        model=EXTRACTION_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    latency_ms = (time.perf_counter() - t0) * 1000
    text = response.choices[0].message.content or ""
    pt, ct = _usage_tokens(response)
    cost = _completion_cost_usd(response)
    meta = {
        "phase": phase,
        "model": EXTRACTION_MODEL,
        "latency_ms": latency_ms,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "cost_usd": cost,
    }
    return _extract_json_object(text), meta


def extract_profile_from_text(
    settings: Settings,
    *,
    url: str,
    page_text: str,
    vertical: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    user = (
        f"Website URL: {url}\n"
        f"Vertical hint: {vertical}\n\n"
        "Extract a JSON object with keys:\n"
        "- brand_name (string, required)\n"
        "- aliases (array of strings)\n"
        "- location (string, city/region/country if known)\n"
        "- services (array of short strings)\n"
        "- competitors (array of competitor firm names if clearly mentioned)\n"
        "- description (short string)\n"
        "- brand_domains (array of domains owned by the brand if obvious)\n\n"
        "Page text:\n"
        f"{page_text[:MAX_TEXT_CHARS]}"
    )
    return _llm_json(
        settings,
        system="You extract business profile fields for GEO analysis. Reply with JSON only.",
        user=user,
        phase="profile_extract",
    )


def enrich_profile_from_url(
    settings: Settings,
    *,
    url: str,
    vertical: str,
    partial: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    host = urlparse(url).netloc
    partial = partial or {}
    brand = str(partial.get("brand_name") or "").strip()
    location = str(partial.get("location") or "").strip()
    user = (
        f"Infer a UK-focused {vertical} business profile from this website URL/domain.\n"
        f"URL: {url}\nHost: {host}\n"
        f"Partial extract (may be empty): {partial}\n\n"
        "Return JSON with keys:\n"
        "- brand_name (string)\n"
        "- aliases (array of strings: trading names, short names, 'Name Ltd' variants — not the primary brand_name)\n"
        "- location (string: prefer a single primary city/town + region/country)\n"
        "- services (array of short strings)\n"
        "- competitors (array of real firm names)\n"
        "- description (short string)\n"
        "- brand_domains (array of domains owned by the brand if obvious)\n\n"
        "Competitor rules:\n"
        "- Prefer local/regional rivals in the same vertical near the inferred location; "
        "then well-known national alternatives if needed.\n"
        "- Use plausible real firm names only; do not invent fake practices.\n"
        "- Exclude the brand itself and obvious aliases of the brand"
        + (f" (brand: {brand})" if brand else "")
        + ".\n"
        "- Return 3–8 competitors when possible; empty array only if truly unknown.\n\n"
        "Do not invent fake UK street addresses or phone numbers. "
        "Prefer plausible best-effort brand_name/location over leaving them empty."
        + (f"\nKnown location hint: {location}" if location else "")
    )
    return _llm_json(
        settings,
        system=(
            "You infer SME business profiles from URLs for GEO competitor analysis. "
            "Reply with JSON only. Competitors must be other firms, never the target brand."
        ),
        user=user,
        phase="profile_enrich",
    )


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        s = str(item).strip()
        if s and s not in out:
            out.append(s)
    return out


def generate_aliases(brand_name: str, aliases: list[str]) -> list[str]:
    merged: list[str] = []
    for name in [brand_name, *aliases]:
        n = name.strip()
        if not n:
            continue
        if n not in merged:
            merged.append(n)
        stripped = _SUFFIX_RE.sub("", n).strip(" ,.-")
        stripped = re.sub(r"\s{2,}", " ", stripped).strip()
        if stripped and stripped.lower() != n.lower() and stripped not in merged:
            merged.append(stripped)
    # Drop primary brand from aliases list (kept separately on profile)
    return [a for a in merged if a.lower() != brand_name.strip().lower()]


_COUNTRY_LIKE = frozenset(
    {
        "uk",
        "u.k.",
        "u.k",
        "united kingdom",
        "england",
        "scotland",
        "wales",
        "northern ireland",
        "gb",
        "great britain",
    }
)


def primary_location(location: str) -> tuple[str, str | None]:
    """Return (primary_location, location_raw_or_None).

    Multi-office strings like \"Bristol, Bath, Yeovil, London, UK\" become \"Bristol, UK\".
    Short strings like \"Manchester, UK\" are left unchanged (raw is None).
    """
    raw = (location or "").strip()
    if not raw:
        return "UK", None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) <= 2:
        return raw, None
    first = parts[0]
    last = parts[-1]
    if last.lower() in _COUNTRY_LIKE:
        primary = f"{first}, {last}"
    else:
        primary = first
    if primary.lower() == raw.lower():
        return raw, None
    return primary, raw


def _filter_competitors(competitors: list[str], *, brand_name: str, aliases: list[str]) -> list[str]:
    blocked = {brand_name.strip().lower(), *(a.strip().lower() for a in aliases if a.strip())}
    out: list[str] = []
    for name in competitors:
        n = name.strip()
        if not n or n.lower() in blocked:
            continue
        if n not in out:
            out.append(n)
    return out[:8]


def _merge_profile_dicts(base: dict[str, Any], enrich: dict[str, Any]) -> dict[str, Any]:
    """Keep non-empty base fields; fill gaps from enrich (lists merge when base list empty)."""
    merged = dict(base)
    for key, value in enrich.items():
        if key in {"competitors", "aliases", "services", "brand_domains"}:
            if not _as_str_list(merged.get(key)):
                merged[key] = value
            continue
        if not str(merged.get(key) or "").strip():
            merged[key] = value
    return merged


def load_accountant_query_templates(pilot_dir: Path) -> list[str]:
    path = pilot_dir / "templates" / "accountants_queries.yaml"
    if not path.is_file():
        # Fallback relative to this package's pilots default layout
        alt = Path(__file__).resolve().parent.parent / "pilots" / "templates" / "accountants_queries.yaml"
        path = alt if alt.is_file() else path
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    queries = raw.get("queries") if isinstance(raw, dict) else None
    if not isinstance(queries, list) or not queries:
        raise FileNotFoundError(f"Accountant query templates not found at {path}")
    return [str(q).strip() for q in queries if str(q).strip()]


def build_queries_from_templates(
    templates: list[str],
    *,
    location: str,
    services: list[str],
) -> list[str]:
    loc = location.strip() or "the UK"
    service = services[0] if services else "small business"
    out: list[str] = []
    for tmpl in templates:
        try:
            q = tmpl.format(location=loc, service=service, brand="")
        except Exception:
            q = tmpl.replace("{location}", loc).replace("{service}", service)
        q = q.strip()
        if q and q not in out:
            out.append(q)
    return out


def profile_dict_to_pilot(
    data: dict[str, Any],
    *,
    url: str,
    vertical: str,
    queries: list[str],
    location_raw: str | None = None,
) -> PilotProfile:
    brand = str(data.get("brand_name") or "").strip()
    if not brand:
        raise ValueError("Could not infer brand_name from URL")
    aliases = generate_aliases(brand, _as_str_list(data.get("aliases")))
    location = str(data.get("location") or "").strip() or "UK"
    host = urlparse(url).netloc.lower().removeprefix("www.")
    domains = _as_str_list(data.get("brand_domains"))
    if host and host not in domains:
        domains = [host, *domains]
    competitors = _filter_competitors(
        _as_str_list(data.get("competitors")),
        brand_name=brand,
        aliases=aliases,
    )
    slug = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return PilotProfile(
        id=f"url-{slug}",
        brand_name=brand,
        location=location,
        competitors=competitors,
        queries=queries,
        brand_domains=domains,
        url=url,
        aliases=aliases,
        industry=vertical,
        services=_as_str_list(data.get("services")),
        location_raw=location_raw,
    )


def infer_pilot_from_url(
    settings: Settings,
    url: str,
    *,
    vertical: str = "accountants",
) -> tuple[PilotProfile, list[dict[str, Any]]]:
    """Fetch/extract/enrich a PilotProfile for URL intake. Returns profile + usage_log entries."""
    vertical = (vertical or "accountants").strip().lower()
    if vertical not in SUPPORTED_VERTICALS:
        raise ValueError(f"Unsupported vertical: {vertical}")

    url = normalize_url(url)
    usage: list[dict[str, Any]] = []

    page_text, fetch_meta = fetch_url_text(url)
    usage.append(fetch_meta)

    extracted: dict[str, Any] = {}
    if len(page_text) >= MIN_USEFUL_TEXT:
        extracted, extract_meta = extract_profile_from_text(
            settings, url=url, page_text=page_text, vertical=vertical
        )
        usage.append(extract_meta)

    brand = str(extracted.get("brand_name") or "").strip()
    location = str(extracted.get("location") or "").strip()
    aliases_so_far = generate_aliases(brand, _as_str_list(extracted.get("aliases"))) if brand else []
    competitors_so_far = _as_str_list(extracted.get("competitors"))
    need_core_enrich = not brand or not location or len(page_text) < MIN_USEFUL_TEXT
    need_gap_enrich = bool(brand and location) and (
        not competitors_so_far or not aliases_so_far
    )
    if need_core_enrich or need_gap_enrich:
        enriched, enrich_meta = enrich_profile_from_url(
            settings, url=url, vertical=vertical, partial=extracted
        )
        usage.append(enrich_meta)
        extracted = _merge_profile_dicts(extracted, enriched)
        if not str(extracted.get("brand_name") or "").strip():
            extracted["brand_name"] = enriched.get("brand_name")
        if not str(extracted.get("location") or "").strip():
            extracted["location"] = enriched.get("location")

    loc_primary, loc_raw = primary_location(str(extracted.get("location") or ""))
    extracted["location"] = loc_primary

    templates = load_accountant_query_templates(settings.pilot_dir_path)
    queries = build_queries_from_templates(
        templates,
        location=loc_primary,
        services=_as_str_list(extracted.get("services")),
    )
    usage.append({"phase": "query_gen", "query_count": len(queries), "cost_usd": 0.0})

    pilot = profile_dict_to_pilot(
        extracted,
        url=url,
        vertical=vertical,
        queries=queries,
        location_raw=loc_raw,
    )
    return pilot, usage


def pilot_snapshot(pilot: PilotProfile) -> dict[str, Any]:
    snap: dict[str, Any] = {
        "id": pilot.id,
        "brand_name": pilot.brand_name,
        "location": pilot.location,
        "url": pilot.url,
        "aliases": list(pilot.aliases),
        "competitors": list(pilot.competitors),
        "queries": list(pilot.queries),
        "services": list(pilot.services),
        "industry": pilot.industry,
        "brand_domains": list(pilot.brand_domains),
    }
    if pilot.location_raw:
        snap["location_raw"] = pilot.location_raw
    return snap
