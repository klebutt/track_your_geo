"""Tests for LiteLLM cost normalization."""

from tygeo.llm import _parse_cost_usd


def test_parse_cost_usd_from_float():
    assert _parse_cost_usd(0.01944) == 0.01944


def test_parse_cost_usd_from_breakdown_dict():
    raw = {"input_tokens_cost": 0.0, "output_tokens_cost": 0.01944, "total_cost": 0.01944}
    assert _parse_cost_usd(raw) == 0.01944


def test_parse_cost_usd_invalid_returns_zero():
    assert _parse_cost_usd("not-a-number") == 0.0
    assert _parse_cost_usd(None) == 0.0
