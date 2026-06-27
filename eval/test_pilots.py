"""Checks for built-in demo pilot configuration."""

from tygeo.hardcoded_pilots import HARDCODED_PILOT_SPECS
from tygeo.pilots import PilotProfile


def test_all_pilots_load_and_have_queries():
    pilots = [PilotProfile.model_validate(spec) for spec in HARDCODED_PILOT_SPECS]
    assert len(pilots) >= 3
    for pilot in pilots:
        assert pilot.queries
        assert pilot.brand_name
        assert pilot.brand_domains


def test_probe_templates_never_include_brand_placeholder():
    for spec in HARDCODED_PILOT_SPECS:
        for template in spec["queries"]:
            assert "{brand}" not in template


def test_sdl_surveying_pilot_present():
    ids = {spec["id"] for spec in HARDCODED_PILOT_SPECS}
    assert "sdl-surveying-uk" in ids
    sdl = next(s for s in HARDCODED_PILOT_SPECS if s["id"] == "sdl-surveying-uk")
    assert sdl["brand_domains"] == ["sdlsurveying.co.uk"]
    assert "e.surv" in sdl["competitors"]
