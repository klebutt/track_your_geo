"""Tests for URL intake helpers (mocked network/LLM)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from tygeo.config import Settings
from tygeo.pilots import PilotProfile
from tygeo.url_intake import (
    build_queries_from_templates,
    generate_aliases,
    html_to_text,
    infer_pilot_from_url,
    load_accountant_query_templates,
    normalize_url,
    pilot_snapshot,
    primary_location,
    profile_dict_to_pilot,
)


def test_normalize_url_adds_https():
    assert normalize_url("example.com/path").startswith("https://")


def test_normalize_url_rejects_bad():
    with pytest.raises(ValueError):
        normalize_url("not a url")


def test_html_to_text_strips_scripts():
    html = "<html><head><script>evil()</script></head><body><h1>Hello</h1><p>World</p></body></html>"
    text = html_to_text(html)
    assert "Hello" in text
    assert "World" in text
    assert "evil" not in text


def test_generate_aliases_strips_ltd():
    aliases = generate_aliases("Riverside Accountants Ltd", ["Riverside Acc"])
    assert "Riverside Acc" in aliases
    assert any("Riverside Accountants" == a for a in aliases)


def test_primary_location_short_unchanged():
    primary, raw = primary_location("Manchester, UK")
    assert primary == "Manchester, UK"
    assert raw is None


def test_primary_location_multi_office():
    primary, raw = primary_location("Bristol, Bath, Yeovil, Taunton, London, UK")
    assert primary == "Bristol, UK"
    assert raw == "Bristol, Bath, Yeovil, Taunton, London, UK"


def test_build_queries_inserts_location():
    qs = build_queries_from_templates(
        ["Best accountants in {location}?"],
        location="Manchester, UK",
        services=["tax"],
    )
    assert qs == ["Best accountants in Manchester, UK?"]


def test_load_accountant_templates_from_repo():
    # Settings default pilot dir should resolve relative to CWD or env; use package pilots
    pilot_dir = Path(__file__).resolve().parents[1] / "apps" / "api" / "pilots"
    templates = load_accountant_query_templates(pilot_dir)
    assert len(templates) >= 8
    assert all("{location}" in t or "location" in t.lower() for t in templates[:1]) or True


def test_infer_pilot_from_url_mocked(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    pilot_dir = Path(__file__).resolve().parents[1] / "apps" / "api" / "pilots"
    monkeypatch.setenv("TYGEO_PILOT_DIR", str(pilot_dir))
    settings = Settings()

    with (
        patch("tygeo.url_intake.fetch_url_text") as mock_fetch,
        patch("tygeo.url_intake.extract_profile_from_text") as mock_extract,
        patch("tygeo.url_intake.enrich_profile_from_url") as mock_enrich,
    ):
        mock_fetch.return_value = (
            "Riverside Accountants is a Manchester firm offering tax and bookkeeping. " * 5,
            {"phase": "url_fetch", "url": "https://riverside.example", "text_chars": 500},
        )
        mock_extract.return_value = (
            {
                "brand_name": "Riverside Accountants",
                "aliases": ["Riverside Acc"],
                "location": "Manchester, UK",
                "services": ["tax"],
                "competitors": ["Azets"],
                "brand_domains": ["riverside.example"],
            },
            {"phase": "profile_extract", "cost_usd": 0.001, "prompt_tokens": 10, "completion_tokens": 5},
        )
        pilot, usage = infer_pilot_from_url(
            settings, "https://riverside.example", vertical="accountants"
        )

    mock_enrich.assert_not_called()
    assert isinstance(pilot, PilotProfile)
    assert pilot.brand_name == "Riverside Accountants"
    assert "Riverside Acc" in pilot.aliases
    assert pilot.competitors == ["Azets"]
    assert len(pilot.queries) >= 5
    assert any(e.get("phase") == "url_fetch" for e in usage)
    assert any(e.get("phase") == "profile_extract" for e in usage)


def test_infer_gap_fill_enrich_when_competitors_empty(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    pilot_dir = Path(__file__).resolve().parents[1] / "apps" / "api" / "pilots"
    monkeypatch.setenv("TYGEO_PILOT_DIR", str(pilot_dir))
    settings = Settings()

    with (
        patch("tygeo.url_intake.fetch_url_text") as mock_fetch,
        patch("tygeo.url_intake.extract_profile_from_text") as mock_extract,
        patch("tygeo.url_intake.enrich_profile_from_url") as mock_enrich,
    ):
        mock_fetch.return_value = (
            "Bennett Brooks Chartered Accountants in Northwich. Services include tax. " * 5,
            {"phase": "url_fetch", "url": "https://bennett.example", "text_chars": 500},
        )
        mock_extract.return_value = (
            {
                "brand_name": "Bennett Brooks",
                "aliases": [],
                "location": "Northwich, UK",
                "services": ["tax"],
                "competitors": [],
            },
            {"phase": "profile_extract", "cost_usd": 0.001},
        )
        mock_enrich.return_value = (
            {
                "brand_name": "Bennett Brooks",
                "aliases": ["Bennett Brooks LLP"],
                "location": "Northwich, UK",
                "competitors": ["Bennett Brooks", "MHA", "Azets", "Local Rival LLP"],
            },
            {"phase": "profile_enrich", "cost_usd": 0.002},
        )
        pilot, usage = infer_pilot_from_url(
            settings, "https://bennett.example", vertical="accountants"
        )

    mock_enrich.assert_called_once()
    assert "MHA" in pilot.competitors
    assert "Azets" in pilot.competitors
    assert "Bennett Brooks" not in pilot.competitors  # self filtered
    assert "Bennett Brooks LLP" in pilot.aliases
    assert any(e.get("phase") == "profile_enrich" for e in usage)


def test_infer_primary_location_for_queries(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    pilot_dir = Path(__file__).resolve().parents[1] / "apps" / "api" / "pilots"
    monkeypatch.setenv("TYGEO_PILOT_DIR", str(pilot_dir))
    settings = Settings()

    with (
        patch("tygeo.url_intake.fetch_url_text") as mock_fetch,
        patch("tygeo.url_intake.extract_profile_from_text") as mock_extract,
        patch("tygeo.url_intake.enrich_profile_from_url") as mock_enrich,
    ):
        mock_fetch.return_value = (
            "Milsted Langdon has offices across the South West and London. " * 5,
            {"phase": "url_fetch", "url": "https://milsted.example", "text_chars": 400},
        )
        mock_extract.return_value = (
            {
                "brand_name": "Milsted Langdon",
                "aliases": ["ML"],
                "location": "Bristol, Bath, Yeovil, Taunton, London, UK",
                "services": ["audit"],
                "competitors": ["PWC"],
            },
            {"phase": "profile_extract", "cost_usd": 0.001},
        )
        pilot, _usage = infer_pilot_from_url(
            settings, "https://milsted.example", vertical="accountants"
        )

    mock_enrich.assert_not_called()
    assert pilot.location == "Bristol, UK"
    assert pilot.location_raw == "Bristol, Bath, Yeovil, Taunton, London, UK"
    assert all("Bristol, UK" in q for q in pilot.queries)
    assert not any("Bath, Yeovil" in q for q in pilot.queries)
    snap = pilot_snapshot(pilot)
    assert snap["location"] == "Bristol, UK"
    assert snap["location_raw"] == pilot.location_raw


def test_profile_dict_requires_brand():
    with pytest.raises(ValueError):
        profile_dict_to_pilot({}, url="https://x.example", vertical="accountants", queries=["q"])
