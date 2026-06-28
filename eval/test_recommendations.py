"""Tests for recommendations enrichment and persistence."""

import json
from unittest.mock import MagicMock, patch

from tygeo.analysis import (
    compute_avg_position_score,
    compute_citation_gaps,
    compute_sentiment_summary,
    execute_run,
    _competitor_wins,
    _missing_or_weak_queries,
)
from tygeo.config import Settings
from tygeo.llm import run_recommendations


def test_compute_sentiment_summary_counts_visible_rows():
    results = [
        {"brand_mentioned": True, "sentiment": "positive"},
        {"brand_mentioned": True, "sentiment": "neutral"},
        {"brand_mentioned": False, "sentiment": "neutral"},
    ]
    summary = compute_sentiment_summary(results)
    assert summary["total_visible"] == 2
    assert summary["total_probes"] == 3
    assert summary["counts"] == {"positive": 1, "neutral": 1, "negative": 0}


def test_compute_citation_gaps_finds_competitor_only_domains():
    results = [
        {
            "brand_mentioned": False,
            "competitors_mentioned": {"Gymkhana": True},
            "cited_domains": [{"domain": "theinfatuation.com", "kind": "third_party"}],
        },
        {
            "brand_mentioned": True,
            "competitors_mentioned": {"Gymkhana": False},
            "cited_domains": [{"domain": "dishoom.com", "kind": "brand_owned"}],
        },
    ]
    gaps = compute_citation_gaps(results, brand_domains=["dishoom.com"])
    assert gaps == [{"domain": "theinfatuation.com", "count": 1}]


def test_compute_avg_position_score_ignores_invisible_rows():
    results = [
        {"brand_mentioned": True, "mention_position": "first_mentioned"},
        {"brand_mentioned": False, "mention_position": "not_mentioned"},
    ]
    assert compute_avg_position_score(results) == 1.0


def test_missing_and_competitor_helpers():
    results = [
        {
            "query_text": "Best brunch in London",
            "brand_mentioned": False,
            "mention_position": "not_mentioned",
            "competitors_mentioned": {"The Ivy": True},
        },
        {
            "query_text": "Indian restaurants in London",
            "brand_mentioned": True,
            "mention_position": "secondary",
            "competitors_mentioned": {"The Ivy": True, "Hawksmoor": False},
        },
    ]
    assert _missing_or_weak_queries(results) == [
        "Best brunch in London",
        "Indian restaurants in London",
    ]
    assert _competitor_wins(results, ["The Ivy", "Hawksmoor"]) == ["The Ivy"]


def test_run_recommendations_includes_enriched_payload():
    settings = Settings(openai_api_key="test-key")
    payload = [
        {
            "title": "Earn coverage on The Infatuation",
            "detail": "Competitors appear on theinfatuation.com but Dishoom does not.",
            "impact": "high",
            "category": "third_party",
        }
    ]
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
    mock_response.usage = MagicMock(prompt_tokens=120, completion_tokens=80)

    with patch("tygeo.llm.litellm.completion", return_value=mock_response) as mock_completion:
        with patch("tygeo.llm._completion_cost_usd", return_value=0.005):
            items, meta = run_recommendations(
                settings,
                brand="Dishoom",
                location="London, UK",
                visibility_rate=0.4,
                composite_score=52.5,
                sentiment_summary={"counts": {"positive": 2, "neutral": 1, "negative": 0}, "total_visible": 3, "total_probes": 10},
                avg_position=0.667,
                citation_gaps=[{"domain": "theinfatuation.com", "count": 2}],
                missing_queries=["Best brunch in London"],
                competitor_wins=["The Ivy"],
            )

    user_payload = json.loads(mock_completion.call_args.kwargs["messages"][1]["content"])
    assert user_payload["composite_geo_score"] == 52.5
    assert user_payload["citation_gaps"][0]["domain"] == "theinfatuation.com"
    assert items[0]["title"].startswith("Earn coverage")
    assert meta["cost_usd"] == 0.005


def test_execute_run_persists_recommendations():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from tygeo.db import Base
    from tygeo.pilots import PilotProfile

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    pilot = PilotProfile(
        id="dishoom-london",
        brand_name="Dishoom",
        location="London, UK",
        competitors=["The Ivy"],
        queries=["Best Indian restaurants in {location}"],
        brand_domains=["dishoom.com"],
        seed_domains=[],
    )
    settings = Settings(tygeo_enabled_probes="model-a", openai_api_key="test-key")

    def fake_probe(settings, model, prompt, *, location=None):
        return (
            "The Ivy and Hawksmoor are popular; Dishoom also gets mentions.",
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
            {"sentiment": "positive", "position": "secondary", "relevance": 0.8},
            {
                "model": "gpt-4o-mini",
                "latency_ms": 5.0,
                "prompt_tokens": 20,
                "completion_tokens": 8,
                "cost_usd": 0.001,
            },
        )

    def fake_recommendations(*args, **kwargs):
        return (
            [
                {
                    "title": "Target The Infatuation",
                    "detail": "Competitors are cited on theinfatuation.com.",
                    "impact": "high",
                    "category": "third_party",
                }
            ],
            {
                "model": "gpt-4o-mini",
                "latency_ms": 8.0,
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "cost_usd": 0.005,
            },
        )

    with patch("tygeo.analysis.run_geo_query_provider", side_effect=fake_probe):
        with patch("tygeo.analysis.extract_mention_details", side_effect=fake_extract):
            with patch("tygeo.analysis.run_recommendations", side_effect=fake_recommendations):
                run = execute_run(
                    db,
                    settings,
                    pilot,
                    brand_override=None,
                    location_override=None,
                )

    assert len(run.recommendations) == 1
    assert run.recommendations[0].title == "Target The Infatuation"
    assert run.total_cost_usd == 0.016
    assert any(entry.get("phase") == "recommendations" for entry in (run.usage_log or []))

    db.close()
