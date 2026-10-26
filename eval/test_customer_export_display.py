"""PDF/markdown display_name and formatting (fictional firms)."""

from datetime import datetime, timezone

from tygeo.customer_export import (
    build_customer_markdown,
    export_customer_report,
    format_query_display,
    prepare_run_for_customer_export,
    prose_brand,
)


def _minimal_run(**overrides):
    run = {
        "status": "completed",
        "brand_name": "Tim-style & Co.",
        "created_at": "2025-06-01T12:00:00Z",
        "model_name": "gpt-5-search-api",
        "visibility_rate": 0.5,
        "composite_score": 40.0,
        "profile_snapshot": {"location": "UK"},
        "query_results": [
            {
                "query_text": "Best firms in the UK — list options?",
                "brand_mentioned": True,
                "competitors_mentioned": {},
                "model_name": "gpt-5-search-api",
            },
        ],
    }
    run.update(overrides)
    return run


def test_manifest_display_name_used_not_legal_dot():
    run = prepare_run_for_customer_export(
        _minimal_run(),
        display_name="Tim-style & Co",
    )
    md = build_customer_markdown(run)
    assert "Tim-style & Co." not in md
    assert "Tim-style & Co" in md
    assert "Co.." not in md


def test_display_name_with_parentheses():
    run = prepare_run_for_customer_export(
        _minimal_run(brand_name="Accounts Direct Ltd"),
        display_name="Accounts Direct (Chester)",
    )
    md = build_customer_markdown(run)
    assert "Accounts Direct (Chester)" in md
    assert "| Firm | Accounts Direct (Chester) |" in md


def test_format_query_display_normalizes_dash_spacing():
    q = "Best firms in the UK  —  list options?"
    assert format_query_display(q) == "Best firms in the UK - list options?"


def test_format_query_display_keeps_intra_word_hyphens():
    q = "Best-rated independent accountant in the UK?"
    assert format_query_display(q) == q


def test_loss_entry_query_uses_dash_normalisation():
    from tygeo.plain_report import LossEntry

    run = prepare_run_for_customer_export(
        {
            "status": "completed",
            "brand_name": "Fictional Firm",
            "model_name": "gpt-5-search-api",
            "visibility_rate": 0.0,
            "composite_score": 10.0,
            "profile_snapshot": {},
            "query_results": [
                {
                    "query_text": "Best firms in the UK  —  list options?",
                    "brand_mentioned": False,
                    "competitors_mentioned": {"Rival Co": True},
                    "model_name": "gpt-5-search-api",
                },
            ],
        },
        display_name="Fictional Firm",
    )
    md = build_customer_markdown(run)
    assert "UK  -  list" not in md
    assert "UK - list" in md


def test_export_report_date_set_on_regenerate_prepare():
    run = prepare_run_for_customer_export(
        _minimal_run(),
        display_name="Tim-style & Co",
        use_export_report_date=True,
    )
    assert run.get("_report_export_date")
    parsed = datetime.fromisoformat(run["_report_export_date"].replace("Z", "+00:00"))
    assert parsed.year >= 2026


def test_prose_brand_strips_trailing_dot_only():
    assert prose_brand("Tim-style & Co.") == "Tim-style & Co"
    assert prose_brand("Accounts Direct (Chester)") == "Accounts Direct (Chester)"
