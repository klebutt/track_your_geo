"""Checks for YAML pilot loading."""

from pathlib import Path

import pytest

from tygeo.config import Settings
from tygeo.pilots import PilotProfile, list_pilots, load_pilot

REPO_ROOT = Path(__file__).resolve().parents[1]
PILOTS_DIR = REPO_ROOT / "pilots"


def test_all_demo_pilots_load_and_have_queries():
    pilots = list_pilots(PILOTS_DIR)
    assert len(pilots) >= 3
    for pilot in pilots:
        assert pilot.queries
        assert pilot.brand_name
        assert pilot.brand_domains


def test_probe_templates_never_include_brand_placeholder():
    for pilot in list_pilots(PILOTS_DIR):
        for template in pilot.queries:
            assert "{brand}" not in template


def test_sdl_surveying_pilot_present():
    sdl = load_pilot(PILOTS_DIR, "sdl-surveying-uk")
    assert sdl is not None
    assert sdl.brand_domains == ["sdlsurveying.co.uk"]
    assert "e.surv" in sdl.competitors


def test_settings_default_pilot_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TYGEO_PILOT_DIR", raising=False)
    settings = Settings(_env_file=None)
    assert settings.tygeo_pilot_dir == "pilots"


def test_temporary_yaml_appears_in_list(tmp_path: Path):
    pilot_dir = tmp_path / "pilots"
    pilot_dir.mkdir()
    (pilot_dir / "test-brand.yaml").write_text(
        "id: test-brand\nbrand_name: Test Brand\nlocation: UK\nqueries:\n  - Best tools in {location}?\n",
        encoding="utf-8",
    )
    pilots = list_pilots(pilot_dir)
    ids = {p.id for p in pilots}
    assert "test-brand" in ids


def test_malformed_yaml_is_skipped(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    pilot_dir = tmp_path / "pilots"
    pilot_dir.mkdir()
    (pilot_dir / "broken.yaml").write_text("not: [valid", encoding="utf-8")
    (pilot_dir / "good.yaml").write_text(
        "id: good-brand\nbrand_name: Good\nlocation: UK\nqueries:\n  - Question in {location}?\n",
        encoding="utf-8",
    )

    with caplog.at_level("WARNING"):
        pilots = list_pilots(pilot_dir)

    assert len(pilots) == 1
    assert pilots[0].id == "good-brand"
    assert any("broken.yaml" in r.message for r in caplog.records)
