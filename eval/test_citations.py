"""Unit tests for citation domain extraction and classification."""

from tygeo.citations import (
    build_cited_domains,
    classify_cited_domains,
    extract_domains,
    extract_domains_from_annotations,
    is_brand_owned,
    normalize_domain,
)


def test_normalize_domain_strips_www():
    assert normalize_domain("www.Example.COM") == "example.com"


def test_extract_domains_from_urls_and_markdown():
    text = (
        "See https://www.timeout.com/london and "
        "[Dishoom](https://dishoom.com/locations) for ideas."
    )
    assert extract_domains(text) == ["timeout.com", "dishoom.com"]


def test_extract_domains_deduplicates():
    text = "https://tripadvisor.com/a and https://www.tripadvisor.com/b"
    assert extract_domains(text) == ["tripadvisor.com"]


def test_extract_domains_empty():
    assert extract_domains("No links here, just Dishoom by name.") == []


def test_is_brand_owned_explicit_domain():
    assert is_brand_owned("dishoom.com", brand_name="Dishoom", brand_domains=["dishoom.com"])


def test_is_brand_owned_heuristic_slug():
    assert is_brand_owned("www.clio.com", brand_name="Clio", brand_domains=[])


def test_extract_domains_from_annotations():
    annotations = [
        {
            "type": "url_citation",
            "url_citation": {
                "url": "https://www.dishoom.com/locations",
                "title": "Dishoom",
            },
        },
        {
            "type": "url_citation",
            "url_citation": {
                "url": "https://timeout.com/london",
                "title": "Time Out",
            },
        },
    ]
    assert extract_domains_from_annotations(annotations) == ["dishoom.com", "timeout.com"]


def test_build_cited_domains_prefers_annotations():
    text = "No urls in prose."
    annotations = [
        {
            "type": "url_citation",
            "url_citation": {"url": "https://dishoom.com/menu", "title": "Dishoom"},
        }
    ]
    cited = build_cited_domains(
        text,
        annotations,
        brand_name="Dishoom",
        brand_domains=["dishoom.com"],
    )
    assert cited == [{"domain": "dishoom.com", "kind": "brand_owned"}]


def test_classify_cited_domains_kinds():
    text = "Try https://dishoom.com and https://timeout.com"
    cited = classify_cited_domains(
        text,
        brand_name="Dishoom",
        brand_domains=["dishoom.com"],
    )
    assert cited == [
        {"domain": "dishoom.com", "kind": "brand_owned"},
        {"domain": "timeout.com", "kind": "third_party"},
    ]
