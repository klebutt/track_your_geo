"""Tests for customer PDF/markdown export (Sales Change-now locks)."""

import re
from pathlib import Path

from tygeo.customer_export import (
    build_customer_markdown,
    export_customer_report,
    pdf_filename_for_firm,
)
from tygeo.plain_report import EM_DASH


def _sample_run(**overrides):
    run = {
        "status": "completed",
        "brand_name": "Hewitt Accountancy",
        "location": "Bristol, UK",
        "model_name": "gpt-5-search-api,perplexity/sonar-pro,gemini/gemini-2.5-flash",
        "visibility_rate": 0.0,
        "composite_score": 16.4,
        "total_cost_usd": 0.58,
        "source_url": "https://www.hewittaccountancy.co.uk/",
        "profile_snapshot": {
            "location": "Bristol, UK",
            "locality_stance": "local_primary",
            "online_remote": "partial",
            "services": ["Tax Advisory", "VAT"],
        },
        "query_results": [
            {
                "query_text": "Best accountant in Bristol, UK?",
                "brand_mentioned": False,
                "competitors_mentioned": {"Bishop Fleming": True},
                "model_name": "gpt-5-search-api",
            },
            {
                "query_text": "Best accountant in Bristol, UK?",
                "brand_mentioned": False,
                "competitors_mentioned": {"Bishop Fleming": True},
                "model_name": "perplexity/sonar-pro",
            },
            {
                "query_text": "Online accountants UK?",
                "brand_mentioned": False,
                "competitors_mentioned": {},
                "model_name": "gpt-5-search-api",
            },
        ],
    }
    run.update(overrides)
    return run


def test_pdf_filename():
    assert pdf_filename_for_firm("Hewitt Accountancy") == "Hewitt-Accountancy-AI-recommend.pdf"
    assert " " not in pdf_filename_for_firm("Hewitt Accountancy")
    assert ":" not in pdf_filename_for_firm("Acme: Tax/Audit")
    assert pdf_filename_for_firm("Acme: Tax/Audit") == "Acme-Tax-Audit-AI-recommend.pdf"


def test_customer_markdown_locks(tmp_path: Path):
    md = build_customer_markdown(_sample_run())
    assert "Get a plain-English action plan for Hewitt Accountancy" in md
    assert "action plan for Bristol" not in md
    assert "Soft" not in md
    # £5-20 pricing line removed; book-a-call CTA instead (2026-10-24)
    assert "£5-20" not in md
    assert "book" in md.lower() and "call" in md.lower()
    assert "email" in md.lower()
    assert "GBP" not in md
    assert "\ufffd" not in md
    assert "£5?20" not in md
    assert "GBP 5?20" not in md
    assert "Mentioned in AI replies" in md
    assert "of replies" in md
    assert "how strongly you are recommended" in md
    assert "cited as a source" in md
    assert "visibility, position, sentiment" not in md
    assert "local_primary" not in md
    assert "gpt-5-search-api" not in md
    assert "perplexity/sonar-pro" not in md
    assert "gemini/gemini-2.5-flash" not in md
    assert "OpenAI search" in md
    assert "Perplexity" in md
    assert "Gemini" in md
    assert EM_DASH not in md
    assert "Best accountant in Bristol, UK?" in md
    assert "Bishop Fleming" in md
    assert "on “Best accountant in Bristol, UK?”" in md or 'on "Best accountant' in md or "- on" in md
    # meaning must not repeat competitor summary
    means_idx = md.index("### What this means")
    means_block = md[means_idx : md.index("### Optional deeper", means_idx)]
    assert "Most often named instead" not in means_block
    assert "Internal notes" not in md
    assert "Run cost" not in md


def test_no_loss_entries_competitor_line_once():
    """Empty loss_entries must not duplicate the 'no tracked competitors' line."""
    run = _sample_run(
        query_results=[
            {
                "query_text": "Win query?",
                "brand_mentioned": True,
                "competitors_mentioned": {},
                "model_name": "gpt-5-search-api",
            },
            {
                "query_text": "Miss query?",
                "brand_mentioned": False,
                "competitors_mentioned": {},
                "model_name": "gpt-5-search-api",
            },
        ]
    )
    md = build_customer_markdown(run)
    who = md[md.index("### Who showed up instead") : md.index("### What this means")]
    needle = "no tracked competitors were named"
    assert who.lower().count(needle) == 1


def test_export_writes_pdf(tmp_path: Path):
    meta = export_customer_report(_sample_run(), tmp_path)
    pdf = Path(meta["pdf_path"])
    assert pdf.exists()
    assert pdf.name == "Hewitt-Accountancy-AI-recommend.pdf"
    assert pdf.stat().st_size > 500
    body = Path(meta["md_path"]).read_text(encoding="utf-8")
    assert "local_primary" not in body
    # £5-20 pricing line removed; book-a-call CTA instead (2026-10-24)
    assert "£5-20" not in body
    assert "book" in body.lower() and "call" in body.lower()
    assert "GBP" not in body
    assert "gpt-5-search-api" not in body


def test_pdf_has_no_raw_markdown_markers(tmp_path: Path):
    """PDF text must not show literal **, *, or markdown '- ' list markers."""
    from pypdf import PdfReader

    meta = export_customer_report(_sample_run(), tmp_path)
    reader = PdfReader(meta["pdf_path"])
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "**" not in text
    assert "*" not in text
    assert "__" not in text
    assert not re.search(r"(?m)^-\s+\S", text)
    assert "Hewitt Accountancy" in text
    # £5-20 pricing line removed; book-a-call CTA instead (2026-10-24)
    assert "£5-20" not in text and "\xa35-20" not in text
    assert "book" in text.lower() or "call" in text.lower()
    assert "GBP" not in text
    # Heading appears once
    assert text.lower().count("your ai recommendation report") == 1
    assert "OpenAI search" in text


def test_pdf_has_run_date(tmp_path: Path):
    """PDF should use run date from run data, not build date."""
    from pypdf import PdfReader

    run = _sample_run(created_at="2026-10-15T10:30:00Z")
    meta = export_customer_report(run, tmp_path)
    reader = PdfReader(meta["pdf_path"])
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "15 October 2026" in text


def test_pdf_header_has_firm_name(tmp_path: Path):
    """PDF header right side should show firm name."""
    from pypdf import PdfReader

    meta = export_customer_report(_sample_run(), tmp_path)
    reader = PdfReader(meta["pdf_path"])
    # Check the first page header area (firm name appears in header)
    first_page = reader.pages[0].extract_text() or ""
    # Firm name should appear (in header and in title block)
    assert first_page.count("Hewitt Accountancy") >= 2


def test_pdf_sample_callout_box(tmp_path: Path):
    """Sample report should have the SAMPLE banner text."""
    from pypdf import PdfReader

    run = _sample_run(
        _sample_banner="SAMPLE REPORT - This uses fictional data for demonstration."
    )
    meta = export_customer_report(run, tmp_path)
    reader = PdfReader(meta["pdf_path"])
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "SAMPLE REPORT" in text
    assert "fictional data" in text


def test_pdf_booking_short_url_in_cta(tmp_path: Path):
    """PDF CTA should use short booking URL (airecommend.co.uk/book)."""
    from pypdf import PdfReader

    meta = export_customer_report(_sample_run(), tmp_path)
    reader = PdfReader(meta["pdf_path"])
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    # CTA should have the short URL, not the raw Google Calendar URL
    assert "airecommend.co.uk/book" in text
    # Should not have raw Google Calendar URL visible
    assert "calendar.app.google" not in text
