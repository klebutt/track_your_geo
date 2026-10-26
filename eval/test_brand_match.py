"""Tests for tolerant brand mention matching (fictional firms only)."""

from tygeo.brand_match import mentions_brand, mentions_phrase


def test_and_vs_ampersand_and_legal_suffix():
    brand = "Harbor Kitchen and Pearce"
    reply = "**Harbor Kitchen & Pearce Ltd** is often recommended for tax."
    assert mentions_brand(reply, brand=brand, aliases=None)


def test_curly_apostrophe_and_extended_trading_name():
    brand = "Sample's Accountants"
    reply = (
        "Consider **Sample\u2019s Accountants & Tax Consultants** for payroll."
    )
    assert mentions_brand(reply, brand=brand, aliases=None)
    reply2 = "Sample\u2019s Accountants and Tax Consultants Ltd can help."
    assert mentions_brand(reply2, brand=brand, aliases=None)


def test_different_firm_sharing_word_not_counted():
    brand = "Riverside & Co"
    reply = "Chris Riverside Management Ltd handles company secretarial work."
    assert not mentions_brand(reply, brand=brand, aliases=None)


def test_same_firm_with_suffix_still_counts():
    brand = "Riverside & Co"
    reply = "We suggest **Riverside & Co Accountants Limited** for VAT."
    assert mentions_brand(reply, brand=brand, aliases=None)


def test_generic_lowercase_request_not_counted():
    brand = "Sampleville Accountants"
    reply = "If you are looking for sampleville accountants, check online directories."
    assert not mentions_brand(reply, brand=brand, aliases=None)


def test_proper_case_generic_brand_still_counts():
    brand = "Sampleville Accountants"
    reply = "Sampleville Accountants have strong reviews in the area."
    assert mentions_brand(reply, brand=brand, aliases=None)


def test_competitor_uses_same_matcher():
    assert mentions_phrase(
        "Try **Northbridge & Partners LLP** for audit.",
        "Northbridge and Partners",
    )
