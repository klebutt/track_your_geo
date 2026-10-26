"""Brand and competitor mention matching in probe response text."""

from __future__ import annotations

import re
import unicodedata

# Strip legal suffixes from the end of a normalized phrase (after lowercasing).
_LEGAL_SUFFIX_RE = re.compile(
    r"\s+(?:limited|ltd\.?|llp|plc|inc\.?)\s*$",
    re.IGNORECASE,
)

_APOSTROPHE_AND_QUOTES = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201b": "'",
        "\u02bc": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
)

_MIN_ALIAS_LEN = 4

_URL_MARKDOWN_RE = re.compile(r"\[([^\]]*)\]\([^)]+\)")
_BARE_URL_RE = re.compile(r"https?://[^\s\]<>\"){}|\\^`\[\]]+", re.IGNORECASE)
_DOMAIN_PATH_RE = re.compile(
    r"\b[a-z0-9](?:[a-z0-9-]*\.)+(?:co\.uk|com|org|net|uk)(?:/[^\s]*)?",
    re.IGNORECASE,
)

_GENERIC_REQUEST_RE = re.compile(
    r"\b(?:looking for|trying to find|find|need|searching for|who are the best|recommend)\s+"
    r"([a-z][a-z'-]*)\s+accountants\b",
    re.IGNORECASE,
)

_GENERIC_LISTING_RE = re.compile(
    r"\b(?:among|top|leading|best|popular|well[- ]known)\s+(?:the\s+)?"
    r"([a-z][a-z'-]*)\s+accountants\b",
    re.IGNORECASE,
)

_CO_TRADING_RE = re.compile(r"^(.+?)\s*&\s*Co\.?$", re.IGNORECASE)

_DIRECTORY_PREFIXES = frozenset(
    {"your", "the", "find", "top", "best", "local", "nearby"}
)


def strip_urls_for_matching(text: str) -> str:
    """Remove link targets and URL/domain paths before mention matching."""
    s = text or ""
    s = _URL_MARKDOWN_RE.sub(lambda m: f" {m.group(1)} " if m.group(1) else " ", s)
    s = _BARE_URL_RE.sub(" ", s)
    s = _DOMAIN_PATH_RE.sub(" ", s)
    return s


def normalize_mention_text(text: str) -> str:
    """Canonical form for token checks (&/and, apostrophes, case, markdown)."""
    s = strip_urls_for_matching(text)
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(_APOSTROPHE_AND_QUOTES)
    s = re.sub(r"\*\*([^*]+)\*\*", r" \1 ", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r" \1 ", s)
    s = s.replace("&", " and ")
    s = re.sub(r"[^\w\s'-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def normalize_mention_phrase(phrase: str) -> str:
    s = normalize_mention_text(phrase)
    s = _LEGAL_SUFFIX_RE.sub("", s).strip()
    return s


def _token_sequence_match(norm_text: str, norm_phrase: str) -> bool:
    needle = norm_phrase.split()
    if not needle:
        return False
    hay = norm_text.split()
    n = len(needle)
    if len(hay) < n:
        return False
    for i in range(len(hay) - n + 1):
        if hay[i : i + n] == needle:
            return True
    return False


def _generic_town_accountants_brand(phrase: str) -> str | None:
    """'{Town} Accountants' (two words, no '&') — town token or None."""
    raw = (phrase or "").strip()
    if "&" in raw or re.search(r"\band\b", raw, re.I):
        return None
    parts = re.findall(r"[A-Za-z']+", raw)
    if len(parts) != 2 or parts[1].lower() != "accountants":
        return None
    return parts[0]


def _has_proper_firm_occurrence(text: str, phrase: str) -> bool:
    """Firm-style casing or markdown emphasis (not generic lowercase prose)."""
    p = (phrase or "").strip()
    if not p:
        return False
    if p in text:
        return True
    if re.search(rf"\*\*\s*{re.escape(p)}\s*\*\*", text, re.IGNORECASE):
        return True
    via = re.search(rf"\bvia\s+{re.escape(p)}\b", text, re.IGNORECASE)
    if via:
        return True
    words = re.findall(r"[A-Za-z']+", p)
    if len(words) >= 2 and words[-1].lower() == "accountants":
        town = words[0]
        if re.search(rf"\b{re.escape(town)}\s+Accountants\b", text):
            return True
    return False


def _only_generic_lowercase_mention(text: str, phrase: str, town: str) -> bool:
    """True when match is only generic lowercase phrasing, not a proper firm name."""
    if _has_proper_firm_occurrence(text, phrase):
        return False
    norm = normalize_mention_text(text)
    norm_phrase = normalize_mention_phrase(phrase)
    if norm_phrase not in norm and not _token_sequence_match(norm, norm_phrase):
        return False
    for match in _GENERIC_REQUEST_RE.finditer(text):
        if match.group(1).lower() == town.lower():
            return True
    for match in _GENERIC_LISTING_RE.finditer(text):
        if match.group(1).lower() == town.lower():
            return True
    # Lowercase "town accountants" without title case on town
    if re.search(
        rf"\b{re.escape(town.lower())}\s+accountants\b",
        text,
        re.IGNORECASE,
    ):
        if not re.search(rf"\b{re.escape(town)}\s+Accountants\b", text):
            return True
    return False


def _is_short_alias(alias: str) -> bool:
    a = (alias or "").strip()
    if not a or " " in a:
        return False
    return len(a) < _MIN_ALIAS_LEN


def _short_alias_matches(text: str, alias: str) -> bool:
    """Aliases under 4 chars: only exact uppercase token (e.g. SA not inside Saffery)."""
    a = (alias or "").strip()
    if not _is_short_alias(a) or not a.isupper():
        return False
    return bool(re.search(rf"(?<![A-Za-z]){re.escape(a)}(?![A-Za-z])", text))


def build_matching_aliases(
    brand: str,
    aliases: list[str] | None = None,
    display_name: str | None = None,
) -> list[str]:
    """Extra names used for matching only (display_name, trading variants)."""
    out: list[str] = []
    seen: set[str] = set()
    primary = (brand or "").strip().lower()

    def add(value: str) -> None:
        v = (value or "").strip()
        if not v:
            return
        key = v.lower()
        if key == primary or key in seen:
            return
        seen.add(key)
        out.append(v)

    for a in aliases or []:
        add(a)
    if display_name:
        add(display_name)

    for source in (brand, display_name or ""):
        m = _CO_TRADING_RE.match(source.strip())
        if m:
            prefix = m.group(1).strip()
            if len(re.sub(r"[^A-Za-z]", "", prefix)) >= 3:
                add(f"{prefix} Accountants")
    return out


def _phrase_blocked_by_directory_prefix(text: str, phrase: str) -> bool:
    """Reject when phrase is part of a longer directory-style name (e.g. Your Town Accountants)."""
    p = (phrase or "").strip()
    if not p:
        return False
    chunks: list[str] = [text]
    chunks.extend(re.findall(r"\*\*([^*]+)\*\*", text))
    chunks.extend(re.findall(r"[\"“”']([^\"“”']+)[\"“”']", text))
    escaped = re.escape(p)
    for chunk in chunks:
        m = re.search(rf"\b([A-Z][a-z]+)\s+{escaped}\b", chunk)
        if m and m.group(1).lower() in _DIRECTORY_PREFIXES:
            return True
    return False


def mentions_phrase(text: str, phrase: str) -> bool:
    """Whether ``phrase`` appears as a whole token sequence in ``text``."""
    phrase = (phrase or "").strip()
    if not phrase:
        return False
    visible = strip_urls_for_matching(text)
    if _phrase_blocked_by_directory_prefix(visible, phrase):
        return False
    norm_text = normalize_mention_text(visible)
    norm_phrase = normalize_mention_phrase(phrase)
    if not norm_phrase or not _token_sequence_match(norm_text, norm_phrase):
        return False

    town = _generic_town_accountants_brand(phrase)
    if town and _only_generic_lowercase_mention(visible, phrase, town):
        return False
    return True


def mentions_brand(
    text: str,
    *,
    brand: str,
    aliases: list[str] | None = None,
) -> bool:
    if mentions_phrase(text, brand):
        return True
    for alias in aliases or []:
        a = (alias or "").strip()
        if not a:
            continue
        if _is_short_alias(a):
            if _short_alias_matches(text, a):
                return True
            continue
        if mentions_phrase(text, a):
            return True
    return False


def sync_mention_position(brand_mentioned: bool, mention_position: str) -> str:
    """Keep mention_position consistent with brand_mentioned."""
    if not brand_mentioned:
        return "not_mentioned"
    if mention_position in ("not_mentioned", "", None):
        return "secondary"
    return mention_position
