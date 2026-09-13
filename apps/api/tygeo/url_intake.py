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
        "- brand_domains (array of domains owned by the brand if obvious)\n"
        "- locality_stance (one of: local_only, local_primary, hybrid, remote_primary, unclear)\n"
        "- online_remote (one of: yes, partial, no, unclear)\n\n"
        "Locality rules: cloud/Xero alone does NOT make hybrid — need UK-wide, nationwide, "
        "or remote-client claims for hybrid/remote_primary. Prefer local_primary when the "
        "site emphasises a town/city catchment.\n\n"
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
    stance = normalize_locality_stance(partial.get("locality_stance"))
    if stance in {"local_only", "local_primary"}:
        competitor_geo = (
            "Prefer independent local/regional rivals near the inferred location first; "
            "add at most 1–2 well-known nationals only if needed to fill the list."
        )
    elif stance == "hybrid":
        competitor_geo = (
            "Mix local/regional rivals near the inferred location with a few UK-wide "
            "or online-capable accountancy brands."
        )
    else:
        competitor_geo = (
            "Prefer plausible UK-wide or online accountancy rivals; include regional "
            "names only when clearly relevant."
        )
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
        "- brand_domains (array of domains owned by the brand if obvious)\n"
        "- locality_stance (one of: local_only, local_primary, hybrid, remote_primary, unclear)\n"
        "- online_remote (one of: yes, partial, no, unclear)\n\n"
        "Competitor rules:\n"
        f"- {competitor_geo}\n"
        "- Use plausible real firm names only; do not invent fake practices.\n"
        "- Exclude the brand itself and obvious aliases of the brand"
        + (f" (brand: {brand})" if brand else "")
        + ".\n"
        "- Return 3–8 competitors when possible; empty array only if truly unknown.\n\n"
        "Locality rules: cloud/Xero alone does NOT make hybrid — need UK-wide/nationwide/"
        "remote-client claims. Prefer local_primary for clear town catchment sites.\n"
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


def normalize_locality_stance(value: object) -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    allowed = {
        "local_only",
        "local_primary",
        "hybrid",
        "remote_primary",
        "unclear",
    }
    if raw in allowed:
        return raw
    return "unclear"


def normalize_online_remote(value: object) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"yes", "partial", "no", "unclear"}:
        return raw
    if raw in {"true", "y"}:
        return "yes"
    if raw in {"false", "n"}:
        return "no"
    return "unclear"


# (local_count, national_count) for a 10-query budget
_STANCE_MIX: dict[str, tuple[int, int]] = {
    "local_only": (10, 0),
    "local_primary": (8, 2),
    "hybrid": (7, 3),
    "remote_primary": (3, 7),
    "unclear": (8, 2),  # treat as local_primary
}


def query_mix_for_stance(stance: str, *, budget: int = 10) -> tuple[int, int]:
    local_n, national_n = _STANCE_MIX.get(normalize_locality_stance(stance), (8, 2))
    total = local_n + national_n
    if total == budget:
        return local_n, national_n
    # Scale if budget differs
    if total <= 0:
        return budget, 0
    local_n = max(0, round(budget * local_n / total))
    national_n = max(0, budget - local_n)
    return local_n, national_n


def geography_note_for_stance(stance: str, *, primary_location: str = "") -> str:
    s = normalize_locality_stance(stance)
    loc = (primary_location or "").strip()
    near = f" near {loc}" if loc and loc.lower() not in {"uk", "united kingdom", "the uk"} else ""
    if s == "local_only":
        return f"Searches focused on local customer-intent questions{near}."
    if s == "local_primary":
        return (
            f"Mostly local searches{near}, with up to two UK-wide/online niche questions."
        )
    if s == "hybrid":
        return (
            f"Mix of local searches{near} and UK-wide/online questions "
            "(about 30% national)."
        )
    if s == "remote_primary":
        return "Mostly UK-wide/online searches, with a few local questions."
    return (
        f"Mostly local searches{near}, with up to two UK-wide/online niche questions "
        "(mix was not certain)."
    )


def load_accountant_query_templates(pilot_dir: Path) -> list[str]:
    """Backward-compatible: flat local list (legacy callers)."""
    banks = load_accountant_query_banks(pilot_dir)
    return list(banks["local"]) or list(banks["national"])


def load_accountant_query_banks(pilot_dir: Path) -> dict[str, list[str]]:
    path = pilot_dir / "templates" / "accountants_queries.yaml"
    if not path.is_file():
        alt = Path(__file__).resolve().parent.parent / "pilots" / "templates" / "accountants_queries.yaml"
        path = alt if alt.is_file() else path
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if not isinstance(raw, dict):
        raise FileNotFoundError(f"Accountant query templates not found at {path}")

    def _list(key: str) -> list[str]:
        items = raw.get(key)
        if not isinstance(items, list):
            return []
        return [str(q).strip() for q in items if str(q).strip()]

    local = _list("local")
    national = _list("national")
    # Legacy flat `queries:` key → all local
    if not local and not national:
        legacy = _list("queries")
        if not legacy:
            raise FileNotFoundError(f"Accountant query templates not found at {path}")
        local = legacy
    return {"local": local, "national": national}


def _format_template(tmpl: str, *, location: str, service: str) -> str:
    try:
        q = tmpl.format(location=location, service=service, brand="")
    except Exception:
        q = tmpl.replace("{location}", location).replace("{service}", service)
    return q.strip()


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
        q = _format_template(tmpl, location=loc, service=service)
        if q and q not in out:
            out.append(q)
    return out


def build_queries_for_stance(
    banks: dict[str, list[str]],
    *,
    stance: str,
    location: str,
    services: list[str],
    budget: int = 10,
) -> list[str]:
    local_n, national_n = query_mix_for_stance(stance, budget=budget)
    loc = location.strip() or "the UK"
    # Avoid stuffing meaningless UK into every "local" slot when location is only country
    if loc.lower() in {"uk", "united kingdom", "the uk", "england"} and local_n:
        # Still run local templates but location reads as UK — prefer shifting toward national
        # only when stance expects locals; keep templates as-is for honesty.
        pass
    service = services[0] if services else "small business"
    local_tmpls = list(banks.get("local") or [])
    national_tmpls = list(banks.get("national") or [])
    out: list[str] = []
    for tmpl in local_tmpls[:local_n]:
        q = _format_template(tmpl, location=loc, service=service)
        if q and q not in out:
            out.append(q)
    for tmpl in national_tmpls[:national_n]:
        q = _format_template(tmpl, location=loc, service=service)
        if q and q not in out:
            out.append(q)
    # Top up from whichever bank still has unused templates
    if len(out) < budget:
        for tmpl in local_tmpls[local_n:] + national_tmpls[national_n:]:
            q = _format_template(tmpl, location=loc, service=service)
            if q and q not in out:
                out.append(q)
            if len(out) >= budget:
                break
    return out[:budget]


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
        locality_stance=normalize_locality_stance(data.get("locality_stance")),
        online_remote=normalize_online_remote(data.get("online_remote")),
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
        # Prefer enrich stance when base missing/unclear
        if normalize_locality_stance(extracted.get("locality_stance")) == "unclear":
            extracted["locality_stance"] = enriched.get("locality_stance")
        if normalize_online_remote(extracted.get("online_remote")) == "unclear":
            extracted["online_remote"] = enriched.get("online_remote")

    loc_primary, loc_raw = primary_location(str(extracted.get("location") or ""))
    extracted["location"] = loc_primary
    extracted["locality_stance"] = normalize_locality_stance(extracted.get("locality_stance"))
    extracted["online_remote"] = normalize_online_remote(extracted.get("online_remote"))

    banks = load_accountant_query_banks(settings.pilot_dir_path)
    queries = build_queries_for_stance(
        banks,
        stance=str(extracted.get("locality_stance") or "unclear"),
        location=loc_primary,
        services=_as_str_list(extracted.get("services")),
    )
    usage.append(
        {
            "phase": "query_gen",
            "query_count": len(queries),
            "locality_stance": extracted["locality_stance"],
            "cost_usd": 0.0,
        }
    )

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
        "locality_stance": pilot.locality_stance,
        "online_remote": pilot.online_remote,
    }
    if pilot.location_raw:
        snap["location_raw"] = pilot.location_raw
    return snap
