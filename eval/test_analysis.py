"""Unit tests for mention detection and scoring helpers."""

from tygeo.analysis import analyze_response, composite_score


def test_analyze_response_brand_and_competitors():
    text = "AcmeLegal CRM is solid; many firms also use Clio."
    brand_hit, comps = analyze_response(
        text,
        brand="AcmeLegal CRM",
        competitors=["Clio", "LexisNexis"],
    )
    assert brand_hit is True
    assert comps["Clio"] is True
    assert comps["LexisNexis"] is False


def test_composite_score_bounds():
    s = composite_score(0.6, brand_mentions=5, total=10)
    assert 0 <= s <= 100
