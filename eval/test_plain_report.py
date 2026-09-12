"""Tests for deterministic plain-language report builder."""

from tygeo.plain_report import build_plain_report


def _row(query: str, *, brand: bool, competitors: dict[str, bool] | None = None, model: str = "m1"):
    return {
        "query_text": query,
        "brand_mentioned": brand,
        "competitors_mentioned": competitors,
        "model_name": model,
    }


def test_plain_report_not_ready_when_running():
    report = build_plain_report(
        status="running",
        brand_name="Acme",
        query_results=[_row("q1", brand=True)],
    )
    assert report.ready is False


def test_plain_report_all_hits():
    rows = [
        _row("Best accountant in Town?", brand=True, model="a"),
        _row("Best accountant in Town?", brand=True, model="b"),
        _row("Tax help near Town?", brand=True, model="a"),
    ]
    report = build_plain_report(
        status="completed",
        brand_name="Acme Tax",
        model_name="a,b",
        query_results=rows,
    )
    assert report.ready is True
    assert report.searches_total == 2
    assert report.searches_recommended == 2
    assert "2 of 2" in report.headline
    assert len(report.win_queries) == 2
    assert report.loss_queries == []


def test_plain_report_multi_model_any_hit_counts():
    """Same query: only one model mentions brand → still a win for that search."""
    rows = [
        _row("Best accountant?", brand=False, model="openai"),
        _row("Best accountant?", brand=True, model="perplexity"),
        _row("Best accountant?", brand=False, model="gemini"),
    ]
    report = build_plain_report(
        status="completed",
        brand_name="Acme",
        model_name="openai,perplexity,gemini",
        query_results=rows,
    )
    assert report.searches_total == 1
    assert report.searches_recommended == 1
    assert report.win_queries == ["Best accountant?"]


def test_plain_report_mixed_wins_and_competitor_losses():
    rows = [
        _row("Win query", brand=True, competitors={"Rival": True}),
        _row("Loss query", brand=False, competitors={"Rival": True}),
        _row("Neither query", brand=False, competitors={"Rival": False}),
    ]
    report = build_plain_report(
        status="completed",
        brand_name="Acme",
        model_name="gpt-5-search-api",
        query_results=rows,
    )
    assert report.searches_total == 3
    assert report.searches_recommended == 1
    assert report.win_queries == ["Win query"]
    assert report.loss_queries == ["Loss query"]
    assert report.gap_summary
    assert "competitor" in report.gap_summary.lower() or "improve" in report.gap_summary.lower()


def test_plain_report_zero_visibility():
    rows = [
        _row("Q1", brand=False, competitors={"Rival": False}),
        _row("Q2", brand=False, competitors={"Rival": True}),
    ]
    report = build_plain_report(
        status="completed",
        brand_name="Ghost Firm",
        query_results=rows,
    )
    assert report.searches_recommended == 0
    assert report.searches_total == 2
    assert "0 of 2" in report.headline
    assert report.loss_queries == ["Q2"]
    assert "did not appear" in (report.gap_summary or "").lower()
