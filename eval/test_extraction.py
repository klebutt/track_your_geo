"""Tests for structured mention extraction."""

import json
from unittest.mock import MagicMock, patch

from tygeo.analysis import (
    aggregate_composite_score,
    composite_score,
    execute_run,
    query_geo_score,
)
from tygeo.config import Settings
from tygeo.llm import EXTRACTION_MODEL, extract_mention_details, normalize_extraction


def test_normalize_extraction_accepts_aliases():
    raw = {
        "sentiment": "POSITIVE",
        "mention_position": "first_mentioned",
        "relevance_score": 0.92,
    }
    out = normalize_extraction(raw)
    assert out == {
        "sentiment": "positive",
        "position": "first_mentioned",
        "relevance": 0.92,
    }


def test_normalize_extraction_clamps_relevance_and_defaults():
    out = normalize_extraction({"sentiment": "bad", "position": "unknown", "relevance": 9})
    assert out["sentiment"] == "neutral"
    assert out["position"] == "not_mentioned"
    assert out["relevance"] == 1.0


def test_normalize_extraction_parses_position_key():
    out = normalize_extraction({"sentiment": "negative", "position": "secondary", "relevance": 0.3})
    assert out["sentiment"] == "negative"
    assert out["position"] == "secondary"
    assert out["relevance"] == 0.3


def test_extract_mention_details_uses_json_mode():
    settings = Settings(openai_api_key="test-key")
    payload = {
        "sentiment": "positive",
        "position": "first_mentioned",
        "relevance": 0.95,
    }
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
    mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20)

    with patch("tygeo.llm.litellm.completion", return_value=mock_response) as mock_completion:
        with patch("tygeo.llm._completion_cost_usd", return_value=0.001):
            extracted, meta = extract_mention_details(
                settings,
                "Dishoom is the best Indian restaurant in London.",
                "Dishoom",
            )

    assert extracted["sentiment"] == "positive"
    assert extracted["position"] == "first_mentioned"
    assert extracted["relevance"] == 0.95
    assert meta["model"] == EXTRACTION_MODEL
    assert meta["cost_usd"] == 0.001
    assert mock_completion.call_args.kwargs["response_format"] == {"type": "json_object"}


def test_extract_mention_details_parses_embedded_json():
    settings = Settings(openai_api_key="test-key")
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='Here is the result: {"sentiment": "neutral", "position": "secondary", "relevance": 0.4}'
            )
        )
    ]
    mock_response.usage = MagicMock(prompt_tokens=50, completion_tokens=10)

    with patch("tygeo.llm.litellm.completion", return_value=mock_response):
        with patch("tygeo.llm._completion_cost_usd", return_value=0.0):
            extracted, _ = extract_mention_details(settings, "Also try Gymkhana.", "Dishoom")

    assert extracted["sentiment"] == "neutral"
    assert extracted["position"] == "secondary"
    assert extracted["relevance"] == 0.4


def test_composite_score_weighted_formula():
    score = composite_score(
        brand_mentioned=True,
        mention_position="first_mentioned",
        sentiment="positive",
        cited_domains=[{"domain": "a.com"}, {"domain": "b.com"}],
    )
    expected = query_geo_score(
        brand_mentioned=True,
        mention_position="first_mentioned",
        sentiment="positive",
        cited_domains=[{"domain": "a.com"}, {"domain": "b.com"}],
    ) * 100.0
    assert score == round(expected, 2)
    assert 0 <= score <= 100


def test_aggregate_composite_score_averages_rows():
    rows = [
        {
            "brand_mentioned": True,
            "mention_position": "first_mentioned",
            "sentiment": "positive",
            "cited_domains": [{"domain": "x.com"}],
        },
        {
            "brand_mentioned": False,
            "mention_position": "not_mentioned",
            "sentiment": "neutral",
            "cited_domains": [],
        },
    ]
    score = aggregate_composite_score(rows)
    assert 0 <= score <= 100


def test_execute_run_skips_extraction_when_brand_not_visible():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from tygeo.db import Base
    from tygeo.pilots import PilotProfile

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    pilot = PilotProfile(
        id="test-pilot",
        brand_name="Dishoom",
        location="London",
        competitors=["Gymkhana"],
        queries=["Best Indian restaurants in {location}"],
        brand_domains=["dishoom.com"],
        seed_domains=[],
    )
    settings = Settings(tygeo_enabled_probes="model-a")

    def fake_probe(settings, model, prompt, *, location=None):
        return (
            "Try Gymkhana and other spots.",
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
        with patch("tygeo.analysis.extract_mention_details") as mock_extract:
            run = execute_run(
                db,
                settings,
                pilot,
                brand_override=None,
                location_override=None,
            )

    mock_extract.assert_not_called()
    assert run.query_results[0].mention_position == "not_mentioned"
    assert all(entry.get("phase") != "extraction" for entry in (run.usage_log or []))

    db.close()


def test_execute_run_runs_extraction_when_brand_visible():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from tygeo.db import Base
    from tygeo.pilots import PilotProfile

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    pilot = PilotProfile(
        id="test-pilot",
        brand_name="Dishoom",
        location="London",
        competitors=["Gymkhana"],
        queries=["Best Indian restaurants in {location}"],
        brand_domains=["dishoom.com"],
        seed_domains=[],
    )
    settings = Settings(tygeo_enabled_probes="model-a")

    def fake_probe(settings, model, prompt, *, location=None):
        return (
            "Dishoom is highly recommended for Indian food in London.",
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

    def fake_extract(settings, answer_text, brand_name):
        return (
            {"sentiment": "positive", "position": "first_mentioned", "relevance": 0.9},
            {
                "model": EXTRACTION_MODEL,
                "latency_ms": 5.0,
                "prompt_tokens": 20,
                "completion_tokens": 8,
                "cost_usd": 0.001,
            },
        )

    with patch("tygeo.analysis.run_geo_query_provider", side_effect=fake_probe):
        with patch("tygeo.analysis.extract_mention_details", side_effect=fake_extract) as mock_extract:
            run = execute_run(
                db,
                settings,
                pilot,
                brand_override=None,
                location_override=None,
            )

    mock_extract.assert_called_once()
    qr = run.query_results[0]
    assert qr.sentiment == "positive"
    assert qr.mention_position == "first_mentioned"
    assert qr.relevance_score == 0.9
    assert run.total_cost_usd == 0.011
    assert any(entry.get("phase") == "extraction" for entry in (run.usage_log or []))

    db.close()
