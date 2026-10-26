"""Tests for rescore preview (no live LLM)."""

from tygeo.rescore import preview_rescore_run


def _run_payload(**overrides):
    base = {
        "status": "completed",
        "brand_name": "Harbor Kitchen and Pearce",
        "profile_snapshot": {
            "brand_name": "Harbor Kitchen and Pearce",
            "aliases": [],
            "competitors": ["Northbridge LLP"],
        },
        "query_results": [
            {
                "query_text": "Q1",
                "response_text": "**Harbor Kitchen & Pearce Ltd** — solid choice.",
                "brand_mentioned": False,
                "competitors_mentioned": {},
                "sentiment": "neutral",
                "mention_position": "not_mentioned",
                "relevance_score": 0.0,
                "cited_domains": [],
            },
            {
                "query_text": "Q2",
                "response_text": "No local firms to suggest.",
                "brand_mentioned": False,
                "competitors_mentioned": {},
                "sentiment": "neutral",
                "mention_position": "not_mentioned",
                "relevance_score": 0.0,
                "cited_domains": [],
            },
        ],
    }
    base.update(overrides)
    return base


def test_preview_rescore_detects_new_mentions():
    stats = preview_rescore_run(_run_payload())
    assert stats.changed
    assert stats.mentions_before == 0
    assert stats.mentions_after == 1
    assert stats.visibility_after > stats.visibility_before


def test_preview_rescore_unchanged_when_already_correct():
    run = _run_payload()
    run["query_results"][0]["brand_mentioned"] = True
    run["query_results"][0]["mention_position"] = "secondary"
    stats = preview_rescore_run(run)
    assert stats.mentions_before == 1
    assert stats.mentions_after == 1
    assert not stats.changed
