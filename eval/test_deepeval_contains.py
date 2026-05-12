"""DeepEval smoke tests (no live LLM calls in this file)."""

from deepeval import assert_test
from deepeval.metrics.base_metric import BaseMetric
from deepeval.test_case import LLMTestCase


class SubstringPresentMetric(BaseMetric):
    """1.0 if needle appears in actual_output (case-insensitive)."""

    def __init__(self, needle: str, threshold: float = 1.0):
        self.needle = needle
        self.threshold = threshold
        self.async_mode = False
        self.strict_mode = False

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        actual = test_case.actual_output or ""
        self.score = 1.0 if self.needle.lower() in actual.lower() else 0.0
        self.success = self.score >= self.threshold
        self.reason = f"substring {self.needle!r}"
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return bool(self.success)

    @property
    def __name__(self):
        return "Substring Present"


def test_deepeval_substring_metric_passes():
    case = LLMTestCase(
        input="Best CRM for UK law firms?",
        actual_output="We recommend AcmeLegal CRM for small conveyancing teams.",
    )
    assert_test(
        case,
        [SubstringPresentMetric("AcmeLegal CRM", threshold=1.0)],
        run_async=False,
    )


def test_deepeval_substring_metric_detects_miss():
    case = LLMTestCase(
        input="Best CRM for UK law firms?",
        actual_output="Consider Clio or Actionstep for practice management.",
    )
    m = SubstringPresentMetric("AcmeLegal CRM", threshold=1.0)
    m.measure(case)
    assert m.is_successful() is False
