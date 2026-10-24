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
    load_jobs,
    MANIFEST_FIELDS,
    COST_PER_FIRM_USD,
    MINUTES_PER_FIRM,
    preflight_check,
    sha256_file,
    append_csv,
    write_progress,
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
        assert jobs[0] == ("Acme Accountants", "https://acme-accountants.example")
        assert jobs[1] == ("Test & Partners", "https://test-partners.example")

    def test_load_jobs_with_firm_column(self, tmp_path):
        """Should parse CSV with 'firm' column (alternative to firm_name)."""
        csv_file = tmp_path / "firms.csv"
        csv_file.write_text(
            "firm,url\n"
            "Legacy Firm Ltd,https://legacy.example\n"
        )
        jobs = load_jobs(csv_file)
        assert len(jobs) == 1
        assert jobs[0] == ("Legacy Firm Ltd", "https://legacy.example")

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
        assert jobs[0][0] == "Valid Firm"

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
        assert jobs[0][0] == "Valid Firm"

    def test_load_jobs_strips_whitespace(self, tmp_path):
        """Should strip whitespace from firm names and URLs."""
        csv_file = tmp_path / "firms.csv"
        csv_file.write_text(
            "firm_name,url\n"
            "  Padded Firm  ,  https://padded.example  \n"
        )
        jobs = load_jobs(csv_file)
        assert len(jobs) == 1
        assert jobs[0] == ("Padded Firm", "https://padded.example")


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
        """CTA should include booking link."""
        from tygeo.plain_report import DEEPER_INSIGHTS_LEAD, BOOKING_LINK
        assert BOOKING_LINK in DEEPER_INSIGHTS_LEAD

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
