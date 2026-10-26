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

_GENERIC_REQUEST_RE = re.compile(
    r"\b(?:looking for|trying to find|find|need|searching for|who are the best|recommend)\s+"
    r"([a-z][a-z'-]*)\s+accountants\b",
    re.IGNORECASE,
)


def normalize_mention_text(text: str) -> str:
    """Canonical form for substring checks (&/and, apostrophes, case, markdown)."""
    s = unicodedata.normalize("NFKC", text or "")
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


def _generic_town_accountants_brand(phrase: str) -> str | None:
    """'{Town} Accountants' (two words, no '&') — town token or None."""
    raw = (phrase or "").strip()
    if "&" in raw or re.search(r"\band\b", raw, re.I):
        return None
    parts = re.findall(r"[A-Za-z']+", raw)
    if len(parts) != 2 or parts[1].lower() != "accountants":
        return None
    return parts[0]


def _has_title_case_firm_occurrence(text: str, town: str) -> bool:
    return re.search(rf"\b{re.escape(town)}\s+Accountants\b", text) is not None


def _only_generic_lowercase_request(text: str, phrase: str, town: str) -> bool:
    """True when the only plausible hit is a lowercase 'looking for {town} accountants' phrase."""
    if _has_title_case_firm_occurrence(text, town):
        return False
    if phrase.strip() in text:
        return False
    norm = normalize_mention_text(text)
    norm_phrase = normalize_mention_phrase(phrase)
    if norm_phrase not in norm:
        return False
    for match in _GENERIC_REQUEST_RE.finditer(text):
        if match.group(1).lower() == town.lower():
            return True
    return False


def mentions_phrase(text: str, phrase: str) -> bool:
    """Whether ``phrase`` appears in ``text`` with tolerant surface-form matching."""
    phrase = (phrase or "").strip()
    if not phrase:
        return False
    norm_text = normalize_mention_text(text)
    norm_phrase = normalize_mention_phrase(phrase)
    if not norm_phrase or norm_phrase not in norm_text:
        return False

    town = _generic_town_accountants_brand(phrase)
    if town and _only_generic_lowercase_request(text, phrase, town):
        return False
    return True


def mentions_brand(
    text: str,
    *,
    brand: str,
    aliases: list[str] | None = None,
) -> bool:
    names = [brand, *(aliases or [])]
    return any(mentions_phrase(text, name) for name in names if (name or "").strip())
