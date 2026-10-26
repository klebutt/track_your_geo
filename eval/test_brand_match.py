"""Tests for tolerant brand mention matching (fictional firms only)."""

from tygeo.brand_match import (
    build_matching_aliases,
    mentions_brand,
    mentions_phrase,
    sync_mention_position,
)


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


def test_short_alias_does_not_match_inside_words():
    brand = "Sampleton Associates"
    reply = "Saffery and Sage are often mentioned for compliance."
    assert not mentions_brand(reply, brand=brand, aliases=["SA"])


def test_short_alias_uppercase_token_counts():
    brand = "Sampleton Associates"
    reply = "The firm SA was noted in a trade list."
    assert mentions_brand(reply, brand=brand, aliases=["SA"])


def test_url_path_does_not_match_town_accountants():
    brand = "Sampleville Accountants"
    reply = (
        "See https://goodcompanies.example/sampleville/accountants and "
        "https://businessfinancing.example/accounting/sampleville-accountants/ for ideas."
    )
    assert not mentions_brand(reply, brand=brand, aliases=None)


def test_generic_top_listing_prose_not_competitor():
    phrase = "Sampleville Accountants"
    reply = "Among top sampleville accountants in the region, several networks appear."
    assert not mentions_phrase(reply, phrase)


def test_via_proper_name_counts_for_competitor():
    phrase = "Sampleville Accountants"
    reply = "Clients often switch via Sampleville Accountants when they outgrow DIY."
    assert mentions_phrase(reply, phrase)


def test_co_trading_alias_accountants_variant():
    brand = "Sam Sample & Co."
    aliases = build_matching_aliases(brand, [], "Sam Sample & Co")
    reply = "We recommend **Sam Sample Accountants** for year-end work."
    assert mentions_brand(reply, brand=brand, aliases=aliases)


def test_directory_your_prefix_not_competitor_match():
    phrase = "Sampleville Accountants"
    reply = (
        '"Your Sampleville Accountants" listings – They list several firms in the area.'
    )
    assert not mentions_phrase(reply, phrase)
    reply2 = "**Your Sampleville Accountants** — provides bookkeeping templates."
    assert not mentions_phrase(reply2, phrase)
    reply3 = "See https://yoursamplevilleaccountants.example/about for a directory."
    assert not mentions_phrase(reply3, phrase)


def test_real_competitor_name_still_matches():
    phrase = "Sampleville Accountants"
    reply = "Clients often choose Sampleville Accountants for year-end accounts."
    assert mentions_phrase(reply, phrase)


def test_sync_mention_position():
    assert sync_mention_position(True, "not_mentioned") == "secondary"
    assert sync_mention_position(False, "first_mentioned") == "not_mentioned"
    assert sync_mention_position(True, "first_mentioned") == "first_mentioned"
