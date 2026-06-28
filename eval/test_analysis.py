"""Unit tests for mention detection and scoring helpers."""

from tygeo.analysis import analyze_response, composite_score, query_geo_score


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
    s = composite_score(
        brand_mentioned=True,
        mention_position="first_mentioned",
        sentiment="positive",
        cited_domains=[{"domain": "example.com"}],
    )
    assert 0 <= s <= 100
    assert s == round(query_geo_score(
        brand_mentioned=True,
        mention_position="first_mentioned",
        sentiment="positive",
        cited_domains=[{"domain": "example.com"}],
    ) * 100.0, 2)
