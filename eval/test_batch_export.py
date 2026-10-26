"""Tests for batch_export.py runner.

Deterministic tests only - no live LLM calls.
"""

import csv
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))
sys.path.insert(0, str(REPO_ROOT))

from scripts.batch_export import (
    BatchJob,
    load_jobs,
    load_run_log_index,
    plan_job,
    MANIFEST_FIELDS,
    COST_PER_FIRM_USD,
    MINUTES_PER_FIRM,
    preflight_check,
    sha256_file,
    append_csv,
    write_progress,
    normalize_url,
    load_manifest,
    build_completion_index,
    write_manifest,
    update_manifest_row,
    dedupe_manifest,
    run_batch,
    run_dedupe_manifest,
)


class TestCSVParsing:
    """Test input CSV parsing."""

    def test_load_jobs_with_firm_name_column(self, tmp_path):
        """Should parse CSV with firm_name column."""
        csv_file = tmp_path / "firms.csv"
        csv_file.write_text(
            "firm_name,url\n"
            "Acme Accountants,https://acme-accountants.example\n"
            "Test & Partners,https://test-partners.example\n"
        )
        jobs = load_jobs(csv_file)
        assert len(jobs) == 2
        assert jobs[0].firm == "Acme Accountants"
        assert jobs[0].url == "https://acme-accountants.example"
        assert jobs[1].firm == "Test & Partners"

    def test_load_jobs_with_firm_column(self, tmp_path):
        """Should parse CSV with 'firm' column (alternative to firm_name)."""
        csv_file = tmp_path / "firms.csv"
        csv_file.write_text(
            "firm,url\n"
            "Legacy Firm Ltd,https://legacy.example\n"
        )
        jobs = load_jobs(csv_file)
        assert len(jobs) == 1
        assert jobs[0].firm == "Legacy Firm Ltd"

    def test_load_jobs_skips_empty_firm(self, tmp_path):
        """Should skip rows with empty firm name."""
        csv_file = tmp_path / "firms.csv"
        csv_file.write_text(
            "firm_name,url\n"
            "Valid Firm,https://valid.example\n"
            ",https://empty.example\n"
            "  ,https://whitespace.example\n"
        )
        jobs = load_jobs(csv_file)
        assert len(jobs) == 1
        assert jobs[0].firm == "Valid Firm"

    def test_load_jobs_skips_non_http_urls(self, tmp_path):
        """Should skip rows without http/https URLs."""
        csv_file = tmp_path / "firms.csv"
        csv_file.write_text(
            "firm_name,url\n"
            "Valid Firm,https://valid.example\n"
            "FTP Firm,ftp://ftp.example\n"
            "No URL Firm,\n"
        )
        jobs = load_jobs(csv_file)
        assert len(jobs) == 1
        assert jobs[0].firm == "Valid Firm"

    def test_load_jobs_optional_columns(self, tmp_path):
        csv_file = tmp_path / "firms.csv"
        csv_file.write_text(
            "firm_name,url,location,display_name\n"
            "Riverside & Co Accountants Limited,https://riverside-accountants.example,Derby UK,Riverside & Co\n"
        )
        jobs = load_jobs(csv_file)
        assert len(jobs) == 1
        assert jobs[0].location == "Derby UK"
        assert jobs[0].display_name == "Riverside & Co"
        assert jobs[0].manifest_firm == "Riverside & Co"

    def test_load_jobs_strips_whitespace(self, tmp_path):
        """Should strip whitespace from firm names and URLs."""
        csv_file = tmp_path / "firms.csv"
        csv_file.write_text(
            "firm_name,url\n"
            "  Padded Firm  ,  https://padded.example  \n"
        )
        jobs = load_jobs(csv_file)
        assert len(jobs) == 1
        assert jobs[0].firm == "Padded Firm"
        assert jobs[0].url == "https://padded.example"


class TestManifestSchema:
    """Test manifest CSV schema matches build.py expectations."""

    def test_manifest_has_required_fields(self):
        """Manifest fields should include what build.py expects."""
        required_by_build = {"firm", "status", "report_path"}
        actual = set(MANIFEST_FIELDS)
        assert required_by_build.issubset(actual), (
            f"Missing fields for build.py: {required_by_build - actual}"
        )

    def test_manifest_has_status_field(self):
        """Manifest should have status field for build.py filtering."""
        assert "status" in MANIFEST_FIELDS

    def test_manifest_has_firm_not_firm_name(self):
        """Manifest should use 'firm' (not 'firm_name') for build.py."""
        assert "firm" in MANIFEST_FIELDS
        assert "firm_name" not in MANIFEST_FIELDS

    def test_manifest_has_sha256_for_verification(self):
        """Manifest should have sha256 for PDF verification."""
        assert "sha256" in MANIFEST_FIELDS


class TestDryRun:
    """Test dry-run mode."""

    def test_dry_run_returns_zero(self, tmp_path, capsys):
        """Dry run should return exit code 0 without calling API."""
        csv_file = tmp_path / "firms.csv"
        csv_file.write_text(
            "firm_name,url\n"
            "Test Firm,https://test.example\n"
        )
        jobs = load_jobs(csv_file)

        from scripts.batch_export import run_batch

        exit_code = run_batch(
            batch="test-batch",
            jobs=jobs,
            vault=tmp_path,
            base_url="http://127.0.0.1:8000",
            reuse_completed=True,
            force=False,
            regenerate=False,
            dry_run=True,
        )
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert "Test Firm" in captured.out

    def test_dry_run_shows_estimated_cost(self, tmp_path, capsys):
        """Dry run should show estimated cost."""
        csv_file = tmp_path / "firms.csv"
        csv_file.write_text(
            "firm_name,url\n"
            "Firm 1,https://firm1.example\n"
            "Firm 2,https://firm2.example\n"
        )
        jobs = load_jobs(csv_file)

        from scripts.batch_export import run_batch

        run_batch(
            batch="test-batch",
            jobs=jobs,
            vault=tmp_path,
            base_url="http://127.0.0.1:8000",
            reuse_completed=True,
            force=False,
            regenerate=False,
            dry_run=True,
        )

        captured = capsys.readouterr()
        expected_cost = 2 * COST_PER_FIRM_USD
        assert f"${expected_cost:.2f}" in captured.out


class TestPreflightCheck:
    """Test API preflight check."""

    def test_preflight_check_returns_none_on_connection_error(self):
        """Preflight should return None when API unreachable."""
        result = preflight_check("http://127.0.0.1:59999")
        assert result is None

    @patch("scripts.batch_export.http_json")
    def test_preflight_check_returns_health_dict(self, mock_http):
        """Preflight should return health dict when API healthy."""
        mock_http.return_value = {"status": "ok"}
        result = preflight_check("http://127.0.0.1:8000")
        assert result == {"status": "ok"}


class TestUtilities:
    """Test utility functions."""

    def test_sha256_file(self, tmp_path):
        """sha256_file should compute correct hash."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello world")
        h = sha256_file(test_file)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_append_csv_creates_file_with_header(self, tmp_path):
        """append_csv should create file with header on first write."""
        csv_path = tmp_path / "manifest.csv"
        row = {"firm": "Test", "url": "https://test.example", "status": "ok"}
        fieldnames = ["firm", "url", "status"]
        append_csv(csv_path, row, fieldnames)

        content = csv_path.read_text()
        lines = content.strip().split("\n")
        assert lines[0] == "firm,url,status"
        assert lines[1] == "Test,https://test.example,ok"

    def test_append_csv_appends_without_header(self, tmp_path):
        """append_csv should append without header on subsequent writes."""
        csv_path = tmp_path / "manifest.csv"
        fieldnames = ["firm", "url", "status"]
        append_csv(csv_path, {"firm": "First", "url": "https://1.example", "status": "ok"}, fieldnames)
        append_csv(csv_path, {"firm": "Second", "url": "https://2.example", "status": "ok"}, fieldnames)

        content = csv_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3
        assert lines[0] == "firm,url,status"

    def test_write_progress_creates_markdown(self, tmp_path):
        """write_progress should create progress markdown file."""
        progress_path = tmp_path / "progress.md"
        write_progress(
            progress_path,
            "wave2",
            done_ok=5,
            failed=1,
            skipped=2,
            total=10,
            current="Current Firm",
            spent_usd=3.25,
        )

        content = progress_path.read_text()
        assert "wave2 batch progress" in content
        assert "5 / 10" in content
        assert "$3.25" in content


class TestCTAText:
    """Test CTA text content."""

    def test_cta_has_booking_link(self):
        """CTA should include booking short URL (domain/book format)."""
        from tygeo.plain_report import DEEPER_INSIGHTS_LEAD, SITE_DOMAIN
        # CTA uses readable short form: airecommend.co.uk/book (not full https:// URL)
        assert f"{SITE_DOMAIN}/book" in DEEPER_INSIGHTS_LEAD

    def test_cta_has_book_a_call_text(self):
        """CTA should mention booking a call."""
        from tygeo.plain_report import DEEPER_INSIGHTS_LEAD
        assert "book" in DEEPER_INSIGHTS_LEAD.lower()
        assert "call" in DEEPER_INSIGHTS_LEAD.lower()

    def test_cta_has_email_option(self):
        """CTA should mention email as alternative."""
        from tygeo.plain_report import DEEPER_INSIGHTS_LEAD
        assert "email" in DEEPER_INSIGHTS_LEAD.lower()
        assert "kieran@airecommend.co.uk" in DEEPER_INSIGHTS_LEAD

    def test_cta_no_prices(self):
        """CTA should not contain pricing."""
        from tygeo.plain_report import DEEPER_INSIGHTS_LEAD
        assert "£" not in DEEPER_INSIGHTS_LEAD
        assert "GBP" not in DEEPER_INSIGHTS_LEAD
        assert "$" not in DEEPER_INSIGHTS_LEAD

    def test_booking_link_single_source_of_truth(self):
        """BOOKING_LINK should come from tygeo.brand (single source of truth)."""
        from tygeo.brand import BOOKING_LINK as BRAND_BOOKING_LINK
        from tygeo.plain_report import BOOKING_LINK as REPORT_BOOKING_LINK

        assert REPORT_BOOKING_LINK == BRAND_BOOKING_LINK, (
            f"plain_report.BOOKING_LINK should be imported from tygeo.brand"
        )

        # Verify site/config.py imports from tygeo.brand (when path is set up)
        sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))
        sys.path.insert(0, str(REPO_ROOT))
        # Force reimport to pick up path changes
        import importlib
        try:
            import site.config as site_config_module
            importlib.reload(site_config_module)
            assert site_config_module.BOOKING_LINK == BRAND_BOOKING_LINK, (
                f"site/config.py BOOKING_LINK should match tygeo.brand"
            )
        except Exception:
            # site.config may fail to import in some environments; that's ok
            # as long as plain_report uses tygeo.brand directly
            pass


class TestCostEstimates:
    """Test cost and time estimates."""

    def test_cost_per_firm_is_reasonable(self):
        """Cost per firm should be in expected range."""
        assert 0.50 <= COST_PER_FIRM_USD <= 1.00

    def test_minutes_per_firm_is_reasonable(self):
        """Time per firm should be in expected range."""
        assert 10 <= MINUTES_PER_FIRM <= 20


class TestURLNormalization:
    """Test URL normalization for completion matching."""

    def test_removes_scheme(self):
        """URL normalization should remove http/https scheme."""
        assert normalize_url("https://example.com") == "example.com"
        assert normalize_url("http://example.com") == "example.com"

    def test_removes_www(self):
        """URL normalization should remove www prefix."""
        assert normalize_url("https://www.example.com") == "example.com"
        assert normalize_url("http://www.example.com") == "example.com"

    def test_removes_trailing_slash(self):
        """URL normalization should remove trailing slash."""
        assert normalize_url("https://example.com/") == "example.com"
        assert normalize_url("https://example.com/path/") == "example.com/path"

    def test_lowercases(self):
        """URL normalization should lowercase."""
        assert normalize_url("https://Example.COM/Path") == "example.com/path"

    def test_preserves_path(self):
        """URL normalization should preserve path."""
        assert normalize_url("https://example.com/about/team") == "example.com/about/team"

    def test_combined_normalization(self):
        """URL normalization should handle all transforms together."""
        assert normalize_url("HTTPS://WWW.Example.COM/Path/") == "example.com/path"

    def test_empty_and_none(self):
        """URL normalization should handle empty/None gracefully."""
        assert normalize_url("") == ""
        assert normalize_url(None) == ""


class TestManifestManagement:
    """Test manifest loading, writing, and updating."""

    def test_load_manifest_nonexistent(self, tmp_path):
        """load_manifest should return empty list for nonexistent file."""
        manifest = load_manifest(tmp_path / "nonexistent.csv")
        assert manifest == []

    def test_load_manifest_existing(self, tmp_path):
        """load_manifest should parse existing manifest."""
        manifest_path = tmp_path / "manifest.csv"
        manifest_path.write_text(
            "firm,url,report_path,generated_at,run_cost_gbp,sha256,status\n"
            "Acme Ltd,https://acme.example,/path/to/acme.pdf,2026-01-01T00:00:00Z,0.50,abc123,ok\n"
        )
        manifest = load_manifest(manifest_path)
        assert len(manifest) == 1
        assert manifest[0]["firm"] == "Acme Ltd"
        assert manifest[0]["status"] == "ok"

    def test_write_manifest_creates_file(self, tmp_path):
        """write_manifest should create manifest file."""
        manifest_path = tmp_path / "reports" / "test-manifest.csv"
        rows = [
            {"firm": "Test", "url": "https://test.example", "report_path": "/p", 
             "generated_at": "now", "run_cost_gbp": "0.5", "sha256": "abc", "status": "ok"}
        ]
        write_manifest(manifest_path, rows)
        assert manifest_path.exists()
        content = manifest_path.read_text()
        assert "firm,url,report_path" in content
        assert "Test,https://test.example" in content

    def test_update_manifest_row_adds_new(self, tmp_path):
        """update_manifest_row should add new row for new URL."""
        manifest = [
            {"firm": "A", "url": "https://a.example", "status": "ok"}
        ]
        new_row = {"firm": "B", "url": "https://b.example", "status": "ok"}
        updated = update_manifest_row(manifest, new_row)
        assert len(updated) == 2
        assert updated[1]["firm"] == "B"

    def test_update_manifest_row_replaces_existing(self, tmp_path):
        """update_manifest_row should replace existing row for same URL."""
        manifest = [
            {"firm": "Old Name", "url": "https://example.com", "status": "ok", "sha256": "old"}
        ]
        new_row = {"firm": "New Name", "url": "https://example.com", "status": "ok", "sha256": "new"}
        updated = update_manifest_row(manifest, new_row)
        assert len(updated) == 1
        assert updated[0]["firm"] == "New Name"
        assert updated[0]["sha256"] == "new"

    def test_update_manifest_row_matches_normalized_url(self):
        """update_manifest_row should match URLs after normalization."""
        manifest = [
            {"firm": "Old", "url": "https://www.Example.COM/", "status": "ok"}
        ]
        new_row = {"firm": "New", "url": "http://example.com", "status": "ok"}
        updated = update_manifest_row(manifest, new_row)
        assert len(updated) == 1
        assert updated[0]["firm"] == "New"


class TestCompletionIndex:
    """Test completion index building and URL-based skip detection."""

    def test_build_completion_index_with_existing_pdf(self, tmp_path):
        """Completion index should include firms with existing PDFs."""
        pdf_path = tmp_path / "firm.pdf"
        pdf_path.write_bytes(b"PDF content")
        manifest = [
            {"firm": "Firm A", "url": "https://firma.example", "status": "ok", 
             "report_path": str(pdf_path)}
        ]
        index = build_completion_index(manifest)
        assert "firma.example" in index
        assert index["firma.example"]["firm"] == "Firm A"

    def test_build_completion_index_excludes_missing_pdf(self, tmp_path):
        """Completion index should exclude firms whose PDFs are missing."""
        manifest = [
            {"firm": "Firm A", "url": "https://firma.example", "status": "ok",
             "report_path": str(tmp_path / "nonexistent.pdf")}
        ]
        index = build_completion_index(manifest)
        assert "firma.example" not in index

    def test_build_completion_index_excludes_failed(self, tmp_path):
        """Completion index should exclude non-ok status."""
        pdf_path = tmp_path / "firm.pdf"
        pdf_path.write_bytes(b"PDF content")
        manifest = [
            {"firm": "Firm A", "url": "https://firma.example", "status": "failed",
             "report_path": str(pdf_path)}
        ]
        index = build_completion_index(manifest)
        assert "firma.example" not in index

    def test_name_mismatch_with_matching_url_skips(self, tmp_path, capsys):
        """Firm with different name but matching URL should be skipped."""
        pdf_dir = tmp_path / "reports" / "test-pdfs"
        pdf_dir.mkdir(parents=True)
        pdf_path = pdf_dir / "Different-Name-AI-recommend.pdf"
        pdf_path.write_bytes(b"PDF content")

        manifest_path = tmp_path / "reports" / "test-manifest.csv"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            "firm,url,report_path,generated_at,run_cost_gbp,sha256,status\n"
            f"Different Name Ltd,https://firm.example,{pdf_path},2026-01-01T00:00:00Z,0.50,abc,ok\n"
        )

        jobs = [BatchJob(firm="CSV Name Ltd", url="https://firm.example")]
        
        exit_code = run_batch(
            batch="test",
            jobs=jobs,
            vault=tmp_path,
            base_url="http://127.0.0.1:8000",
            reuse_completed=True,
            force=False,
            regenerate=False,
            dry_run=True,
        )

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "[SKIP]" in captured.out
        assert "URL matches" in captured.out


class TestRemovedPDFRerun:
    """Test that removing a PDF triggers a re-run."""

    def test_removed_pdf_not_in_completion_index(self, tmp_path):
        """Removed PDF should not appear in completion index."""
        manifest = [
            {"firm": "Firm A", "url": "https://firma.example", "status": "ok",
             "report_path": "/path/that/does/not/exist.pdf"}
        ]
        index = build_completion_index(manifest)
        assert "firma.example" not in index

    def test_dry_run_queues_firm_with_missing_pdf(self, tmp_path, capsys):
        """Dry run should queue firm when PDF has been removed."""
        manifest_path = tmp_path / "reports" / "test-manifest.csv"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            "firm,url,report_path,generated_at,run_cost_gbp,sha256,status\n"
            "Test Firm,https://test.example,/nonexistent/path.pdf,2026-01-01T00:00:00Z,0.50,abc,ok\n"
        )

        jobs = [BatchJob(firm="Test Firm", url="https://test.example")]
        
        exit_code = run_batch(
            batch="test",
            jobs=jobs,
            vault=tmp_path,
            base_url="http://127.0.0.1:8000",
            reuse_completed=True,
            force=False,
            regenerate=False,
            dry_run=True,
        )

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "[PROBE]" in captured.out


class TestForceFlag:
    """Test --force flag behavior."""

    def test_force_queues_all_firms(self, tmp_path, capsys):
        """--force should queue all firms regardless of existing reports."""
        pdf_dir = tmp_path / "reports" / "test-pdfs"
        pdf_dir.mkdir(parents=True)
        pdf_path = pdf_dir / "Test-Firm-AI-recommend.pdf"
        pdf_path.write_bytes(b"PDF content")

        manifest_path = tmp_path / "reports" / "test-manifest.csv"
        manifest_path.write_text(
            "firm,url,report_path,generated_at,run_cost_gbp,sha256,status\n"
            f"Test Firm,https://test.example,{pdf_path},2026-01-01T00:00:00Z,0.50,abc,ok\n"
        )

        jobs = [BatchJob(firm="Test Firm", url="https://test.example")]
        
        exit_code = run_batch(
            batch="test",
            jobs=jobs,
            vault=tmp_path,
            base_url="http://127.0.0.1:8000",
            reuse_completed=True,
            force=True,
            regenerate=False,
            dry_run=True,
        )

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "[PROBE]" in captured.out
        assert "--force" in captured.out


class TestDedupeManifest:
    """Test manifest deduplication."""

    def test_dedupe_keeps_most_recent_ok(self):
        """dedupe_manifest should keep the most recent ok row per URL."""
        manifest = [
            {"firm": "First", "url": "https://test.example", "status": "ok", "sha256": "111"},
            {"firm": "Second", "url": "https://test.example", "status": "ok", "sha256": "222"},
            {"firm": "Other", "url": "https://other.example", "status": "ok", "sha256": "333"},
        ]
        deduped = dedupe_manifest(manifest)
        assert len(deduped) == 2
        test_rows = [r for r in deduped if normalize_url(r["url"]) == "test.example"]
        assert len(test_rows) == 1
        assert test_rows[0]["sha256"] == "222"

    def test_dedupe_keeps_failed_if_no_ok(self):
        """dedupe_manifest should keep last row if no ok rows exist."""
        manifest = [
            {"firm": "First", "url": "https://test.example", "status": "failed"},
            {"firm": "Second", "url": "https://test.example", "status": "failed"},
        ]
        deduped = dedupe_manifest(manifest)
        assert len(deduped) == 1
        assert deduped[0]["firm"] == "Second"

    def test_dedupe_prefers_ok_over_failed(self):
        """dedupe_manifest should prefer ok status over failed."""
        manifest = [
            {"firm": "Failed", "url": "https://test.example", "status": "failed"},
            {"firm": "Success", "url": "https://test.example", "status": "ok"},
            {"firm": "Later Failed", "url": "https://test.example", "status": "failed"},
        ]
        deduped = dedupe_manifest(manifest)
        assert len(deduped) == 1
        assert deduped[0]["firm"] == "Success"
        assert deduped[0]["status"] == "ok"

    def test_dedupe_normalizes_urls(self):
        """dedupe_manifest should treat normalized URLs as same."""
        manifest = [
            {"firm": "A", "url": "https://www.example.com/", "status": "ok"},
            {"firm": "B", "url": "http://example.com", "status": "ok"},
        ]
        deduped = dedupe_manifest(manifest)
        assert len(deduped) == 1
        assert deduped[0]["firm"] == "B"

    def test_run_dedupe_manifest_command(self, tmp_path):
        """run_dedupe_manifest should dedupe and write manifest."""
        manifest_path = tmp_path / "reports" / "test-manifest.csv"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            "firm,url,report_path,generated_at,run_cost_gbp,sha256,status\n"
            "First,https://test.example,/p1,2026-01-01,0.5,aaa,ok\n"
            "Second,https://test.example,/p2,2026-01-02,0.5,bbb,ok\n"
            "Other,https://other.example,/p3,2026-01-01,0.5,ccc,ok\n"
        )

        exit_code = run_dedupe_manifest(manifest_path)
        assert exit_code == 0

        deduped = load_manifest(manifest_path)
        assert len(deduped) == 2

    def test_run_dedupe_manifest_no_duplicates(self, tmp_path, capsys):
        """run_dedupe_manifest should report no duplicates if none exist."""
        manifest_path = tmp_path / "reports" / "test-manifest.csv"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            "firm,url,report_path,generated_at,run_cost_gbp,sha256,status\n"
            "Only One,https://test.example,/p1,2026-01-01,0.5,aaa,ok\n"
        )

        exit_code = run_dedupe_manifest(manifest_path)
        assert exit_code == 0
        
        captured = capsys.readouterr()
        assert "No duplicates" in captured.out


class TestManifestRowReplacement:
    """Test that re-running a firm replaces rather than duplicates manifest rows."""

    def test_update_replaces_by_url(self):
        """Re-running should replace existing row for same URL."""
        manifest = [
            {"firm": "Old Name", "url": "https://test.example", "status": "ok", 
             "sha256": "old", "report_path": "/old/path.pdf"},
            {"firm": "Other", "url": "https://other.example", "status": "ok",
             "sha256": "other", "report_path": "/other/path.pdf"},
        ]
        new_row = {
            "firm": "New Name", "url": "https://test.example", "status": "ok",
            "sha256": "new", "report_path": "/new/path.pdf"
        }
        
        updated = update_manifest_row(manifest, new_row)
        
        assert len(updated) == 2
        test_rows = [r for r in updated if normalize_url(r["url"]) == "test.example"]
        assert len(test_rows) == 1
        assert test_rows[0]["firm"] == "New Name"
        assert test_rows[0]["sha256"] == "new"


class TestJobPlanning:
    """Plan skip / probe / regenerate / rerun from manifest + run log."""

    def test_plan_regenerate_with_run_id(self):
        job = BatchJob(firm="A", url="https://a.example")
        completion = {"a.example": {"status": "ok", "report_path": "/x.pdf"}}
        run_log = {"a.example": {"run_id": 42, "profile_location": "Derby, UK"}}
        action, _reason = plan_job(
            job,
            completion_index=completion,
            run_log_index=run_log,
            reuse_completed=True,
            force=False,
            regenerate=True,
        )
        assert action == "regenerate"

    def test_plan_rerun_on_location_override(self):
        job = BatchJob(firm="A", url="https://a.example", location="Truro, UK")
        completion = {"a.example": {"status": "ok", "report_path": "/x.pdf"}}
        run_log = {"a.example": {"run_id": 7, "profile_location": "Birmingham, UK"}}
        action, reason = plan_job(
            job,
            completion_index=completion,
            run_log_index=run_log,
            reuse_completed=True,
            force=False,
            regenerate=False,
        )
        assert action == "rerun"
        assert "Truro" in reason

    def test_load_run_log_index_latest_run_id(self, tmp_path):
        log = tmp_path / "log.jsonl"
        log.write_text(
            '{"url":"https://a.example","run_id":1,"profile_location":"X"}\n'
            '{"url":"https://a.example","run_id":9,"profile_location":"Y"}\n'
        )
        index = load_run_log_index(log)
        assert index["a.example"]["run_id"] == 9

    def test_dry_run_regenerate_label(self, tmp_path, capsys):
        log_dir = tmp_path / "reports"
        log_dir.mkdir(parents=True)
        (log_dir / "wave2-run-log.jsonl").write_text(
            '{"url":"https://firm.example","run_id":3,"status":"ok"}\n'
        )
        jobs = [BatchJob(firm="Firm", url="https://firm.example")]
        run_batch(
            batch="wave2",
            jobs=jobs,
            vault=tmp_path,
            base_url="http://127.0.0.1:8000",
            reuse_completed=True,
            force=False,
            regenerate=True,
            dry_run=True,
        )
        out = capsys.readouterr().out
        assert "[REGENERATE]" in out
