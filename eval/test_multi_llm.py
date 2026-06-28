"""Tests for multi-model probe fan-out."""

from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tygeo.analysis import execute_run
from tygeo.config import Settings
from tygeo.db import Base
from tygeo.pilots import PilotProfile


def _make_pilot() -> PilotProfile:
    return PilotProfile(
        id="test-pilot",
        brand_name="Dishoom",
        location="London",
        competitors=["Gymkhana"],
        queries=["Best Indian restaurants in {location}"],
        brand_domains=["dishoom.com"],
        seed_domains=[],
    )


def test_enabled_probe_models_splits_csv():
    settings = Settings(tygeo_enabled_probes="gpt-4o-mini-search-preview,perplexity/sonar-pro")
    assert settings.enabled_probe_models == [
        "gpt-4o-mini-search-preview",
        "perplexity/sonar-pro",
    ]


def test_execute_run_fan_out_per_query():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    pilot = _make_pilot()
    settings = Settings(tygeo_enabled_probes="model-a,model-b")

    def fake_probe(settings, model, prompt, *, location=None):
        return (
            f"answer from {model}",
            {
                "model": model,
                "probe_path": "test",
                "latency_ms": 10.0,
                "prompt_tokens": 5,
                "completion_tokens": 10,
                "cost_usd": 0.01,
            },
            [],
            [],
            None,
        )

    with patch("tygeo.analysis.run_geo_query_provider", side_effect=fake_probe):
        run = execute_run(
            db,
            settings,
            pilot,
            brand_override=None,
            location_override=None,
        )

    assert run.model_name == "model-a,model-b"
    assert len(run.query_results) == 2
    models = {qr.model_name for qr in run.query_results}
    assert models == {"model-a", "model-b"}
    assert run.total_cost_usd == 0.02
    assert run.total_prompt_tokens == 10
    assert run.total_completion_tokens == 20

    db.close()
