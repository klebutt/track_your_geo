"""Unit tests for probe rate-limit retry / pacing helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tygeo.analysis import (
    _is_rate_limit_error,
    _needs_openai_pace,
    _retry_after_seconds,
    run_geo_query_provider_with_retries,
)


def test_is_rate_limit_error_detects_litellm_style():
    class RateLimitError(Exception):
        pass

    assert _is_rate_limit_error(RateLimitError("Rate limit reached … 429"))
    assert _is_rate_limit_error(Exception("Error code: 429 - rate_limit_exceeded"))
    assert not _is_rate_limit_error(ValueError("bad request"))


def test_retry_after_seconds_parses_ms_and_seconds():
    sleep_ms, parsed_ms = _retry_after_seconds(Exception("try again in 710ms"))
    assert parsed_ms is True
    assert 0.7 < sleep_ms < 1.2
    sleep_s, parsed_s = _retry_after_seconds(Exception("Please try again in 1.2s."))
    assert parsed_s is True
    assert 1.3 < sleep_s < 2.0
    sleep_sec, parsed_sec = _retry_after_seconds(Exception("try again in 2 seconds"))
    assert parsed_sec is True
    assert 2.0 <= sleep_sec < 3.0
    sleep_def, parsed_def = _retry_after_seconds(Exception("no hint"))
    assert parsed_def is False
    assert sleep_def == 2.0


def test_needs_openai_pace():
    assert _needs_openai_pace("gpt-5-search-api")
    assert _needs_openai_pace("openai/gpt-4o")
    assert not _needs_openai_pace("perplexity/sonar-pro")
    assert not _needs_openai_pace("gemini/gemini-2.5-flash")


def test_run_geo_query_provider_retries_rate_limit_then_succeeds():
    settings = MagicMock()
    ok = ("text", {"cost_usd": 0.01}, [], [], None)
    rate = Exception(
        "RateLimitError: Rate limit reached … Please try again in 10ms. code: rate_limit_exceeded"
    )

    with (
        patch("tygeo.analysis.run_geo_query_provider", side_effect=[rate, ok]) as mock_probe,
        patch("tygeo.analysis.time.sleep") as mock_sleep,
    ):
        result = run_geo_query_provider_with_retries(
            settings,
            "gpt-5-search-api",
            "Best accountant?",
            location="Oxford, UK",
            max_attempts=4,
        )

    assert result == ok
    assert mock_probe.call_count == 2
    assert mock_sleep.call_count == 1
    # OpenAI TPM: ignore short provider hints; sleep at least 45s
    assert mock_sleep.call_args.args[0] >= 45.0


def test_run_geo_query_provider_gives_up_after_max_attempts():
    settings = MagicMock()
    rate = Exception("Error code: 429 - rate_limit_exceeded. try again in 5ms")

    with (
        patch("tygeo.analysis.run_geo_query_provider", side_effect=rate) as mock_probe,
        patch("tygeo.analysis.time.sleep"),
    ):
        with pytest.raises(Exception, match="429"):
            run_geo_query_provider_with_retries(
                settings,
                "gpt-5-search-api",
                "Best accountant?",
                max_attempts=3,
            )

    assert mock_probe.call_count == 3


def test_non_rate_limit_errors_are_not_retried():
    settings = MagicMock()

    with (
        patch(
            "tygeo.analysis.run_geo_query_provider",
            side_effect=RuntimeError("boom"),
        ) as mock_probe,
        patch("tygeo.analysis.time.sleep") as mock_sleep,
    ):
        with pytest.raises(RuntimeError, match="boom"):
            run_geo_query_provider_with_retries(
                settings,
                "gpt-5-search-api",
                "Best accountant?",
                max_attempts=5,
            )

    assert mock_probe.call_count == 1
    mock_sleep.assert_not_called()


def test_non_openai_uses_parsed_short_delay():
    settings = MagicMock()
    ok = ("text", {}, [], [], None)
    rate = Exception("Rate limit reached. Please try again in 50ms")

    with (
        patch("tygeo.analysis.run_geo_query_provider", side_effect=[rate, ok]),
        patch("tygeo.analysis.time.sleep") as mock_sleep,
    ):
        run_geo_query_provider_with_retries(
            settings,
            "perplexity/sonar-pro",
            "q",
            max_attempts=3,
        )

    assert mock_sleep.call_args.args[0] < 5.0
