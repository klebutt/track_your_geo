"""Shared pytest hooks and markers for eval/."""

import os

import pytest

requires_openai_api_key = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set (needed for execute_run credential gate)",
)
