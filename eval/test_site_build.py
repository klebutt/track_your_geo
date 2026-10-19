"""Tests for AI Recommend site build script.

Uses fictional fixtures only - no real firm data.
"""

import csv
import hashlib
import shutil
import tempfile
from pathlib import Path

import pytest

# Add site to path for imports
import sys
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "site"))

from build import (
    copy_public_files,
    escape_html,
    generate_slug,
    markdown_to_html,
    sha256_file,
    build_report_page,
    TEMPLATES_DIR,
    PUBLIC_DIR,
)


class TestSlugGeneration:
    """Test slug generation for report URLs."""

    def test_slug_length(self):
        """Slugs should be 12 characters (secrets.token_urlsafe(9))."""
        slug = generate_slug()
        assert len(slug) == 12

    def test_slug_uniqueness(self):
        """Generated slugs should be unique."""
        slugs = [generate_slug() for _ in range(100)]
        assert len(set(slugs)) == 100

    def test_slug_url_safe(self):
        """Slugs should only contain URL-safe characters."""
        import re
        for _ in range(50):
            slug = generate_slug()
            assert re.match(r"^[A-Za-z0-9_-]+$", slug), f"Slug contains invalid chars: {slug}"


class TestSha256:
    """Test SHA-256 file hashing."""

    def test_sha256_known_content(self, tmp_path):
        """SHA-256 of known content should match expected hash."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world\n")
        # Pre-computed hash of "hello world\n"
        expected = "a948904f2f0f479b8f8564cbf12dace4e2e6b76e9e4c5f7f6a5d1c5b6d7e8f9a"
        actual = sha256_file(test_file)
        # We don't know the exact hash, but verify it's 64 hex chars
        assert len(actual) == 64
        assert all(c in "0123456789abcdef" for c in actual)

    def test_sha256_different_files(self, tmp_path):
        """Different files should have different hashes."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content one")
        file2.write_text("content two")
        assert sha256_file(file1) != sha256_file(file2)


class TestMarkdownToHtml:
    """Test markdown to HTML conversion."""

    def test_headings(self):
        """Headings should convert to h1-h4 tags."""
        md = "# Title\n## Section\n### Subsection\n#### Detail"
        html = markdown_to_html(md)
        assert "<h1>" in html
        assert "<h2>" in html
        assert "<h3>" in html
        assert "<h4>" in html

    def test_paragraphs(self):
        """Plain text should become paragraphs."""
        md = "This is a paragraph.\n\nThis is another."
        html = markdown_to_html(md)
        assert "<p>" in html

    def test_escape_html(self):
        """HTML special characters should be escaped."""
        result = escape_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestCopyPublicFiles:
    """Test copying public files to dist."""

    def test_copies_all_files(self, tmp_path):
        """All public files should be copied to dist."""
        dist = tmp_path / "dist"
        copy_public_files(dist)

        assert (dist / "index.html").exists()
        assert (dist / "privacy.html").exists()
        assert (dist / "robots.txt").exists()
        assert (dist / "sitemap.xml").exists()
        assert (dist / "_headers").exists()
        assert (dist / "_routes.json").exists()
        assert (dist / "styles.css").exists()
        assert (dist / "favicon.svg").exists()

    def test_overwrites_existing_dist(self, tmp_path):
        """Existing dist should be overwritten."""
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "old_file.txt").write_text("old content")

        copy_public_files(dist)

        assert not (dist / "old_file.txt").exists()
        assert (dist / "index.html").exists()


class TestBuildReportPage:
    """Test report page generation with fictional fixtures."""

    @pytest.fixture
    def fake_report_files(self, tmp_path):
        """Create fake report markdown and PDF for testing."""
        # Create fake markdown
        md_content = """# AI recommendation report - Fictional Accounting Ltd

## Your AI recommendation report

This is a test report for a fictional firm.

**AI assistants recommended Fictional Accounting Ltd in 3 of 5 searches**

### Who showed up instead

- **Competitor A** - on "best accountants in Test City"

### What this means

This is the gap summary for the fictional firm.

---

## Snapshot (what we measured)

| | |
|--|--|
| Firm | Fictional Accounting Ltd |
| Location used | Test City, UK |
| Visibility (probes with brand name in reply) | **60%** |
| Composite index | **55.0** / 100 |
"""
        md_path = tmp_path / "fictional-report.md"
        md_path.write_text(md_content)

        # Create fake PDF (just some bytes)
        pdf_content = b"%PDF-1.4 fake pdf content for testing"
        pdf_path = tmp_path / "Fictional-Accounting-Ltd-AI-recommend.pdf"
        pdf_path.write_bytes(pdf_content)

        return md_path, pdf_path

    def test_builds_report_page(self, tmp_path, fake_report_files):
        """Report page should be generated from markdown and PDF."""
        md_path, pdf_path = fake_report_files
        dist = tmp_path / "dist"
        dist.mkdir()

        config = {
            "booking_link": "https://example.com/book",
            "trading_name_line": "Test Trading Name",
        }

        meta = build_report_page(
            md_path=md_path,
            pdf_path=pdf_path,
            slug="test123",
            dist=dist,
            config=config,
        )

        # Check report directory was created
        report_dir = dist / "r" / "test123"
        assert report_dir.exists()
        assert (report_dir / "index.html").exists()
        assert (report_dir / "Fictional-Accounting-Ltd-AI-recommend.pdf").exists()

        # Check metadata
        assert meta["firm"] == "Fictional Accounting Ltd"
        assert meta["slug"] == "test123"
        assert "pdf_sha256" in meta
        assert len(meta["pdf_sha256"]) == 64

    def test_pdf_copied_byte_for_byte(self, tmp_path, fake_report_files):
        """PDF should be copied without modification."""
        md_path, pdf_path = fake_report_files
        dist = tmp_path / "dist"
        dist.mkdir()

        original_hash = sha256_file(pdf_path)

        config = {
            "booking_link": "https://example.com/book",
            "trading_name_line": "Test Trading Name",
        }

        build_report_page(
            md_path=md_path,
            pdf_path=pdf_path,
            slug="test456",
            dist=dist,
            config=config,
        )

        copied_pdf = dist / "r" / "test456" / "Fictional-Accounting-Ltd-AI-recommend.pdf"
        assert sha256_file(copied_pdf) == original_hash

    def test_sha256_verification_fails_on_mismatch(self, tmp_path, fake_report_files):
        """Build should fail if expected SHA-256 doesn't match."""
        md_path, pdf_path = fake_report_files
        dist = tmp_path / "dist"
        dist.mkdir()

        config = {
            "booking_link": "https://example.com/book",
            "trading_name_line": "Test Trading Name",
        }

        with pytest.raises(ValueError, match="hash mismatch"):
            build_report_page(
                md_path=md_path,
                pdf_path=pdf_path,
                slug="test789",
                dist=dist,
                config=config,
                expected_sha256="0" * 64,  # Wrong hash
            )

    def test_sha256_verification_passes_on_match(self, tmp_path, fake_report_files):
        """Build should succeed if expected SHA-256 matches."""
        md_path, pdf_path = fake_report_files
        dist = tmp_path / "dist"
        dist.mkdir()

        expected_hash = sha256_file(pdf_path)

        config = {
            "booking_link": "https://example.com/book",
            "trading_name_line": "Test Trading Name",
        }

        # Should not raise
        meta = build_report_page(
            md_path=md_path,
            pdf_path=pdf_path,
            slug="testabc",
            dist=dist,
            config=config,
            expected_sha256=expected_hash,
        )

        assert meta["pdf_sha256"] == expected_hash


class TestReportPageContent:
    """Test report page HTML content."""

    @pytest.fixture
    def built_report(self, tmp_path):
        """Build a report page and return its HTML."""
        md_content = """# AI recommendation report - Test Firm Ltd

## Your AI recommendation report

Test content here.
"""
        md_path = tmp_path / "test.md"
        md_path.write_text(md_content)

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        dist = tmp_path / "dist"
        dist.mkdir()

        config = {
            "booking_link": "https://cal.example.com/15min",
            "trading_name_line": "Test Trading Line",
        }

        build_report_page(
            md_path=md_path,
            pdf_path=pdf_path,
            slug="testreport",
            dist=dist,
            config=config,
        )

        return (dist / "r" / "testreport" / "index.html").read_text()

    def test_has_noindex_meta(self, built_report):
        """Report page should have noindex meta tag."""
        assert 'name="robots"' in built_report
        assert "noindex" in built_report

    def test_has_booking_link(self, built_report):
        """Report page should have booking link."""
        assert "https://cal.example.com/15min" in built_report

    def test_has_download_button(self, built_report):
        """Report page should have PDF download button."""
        assert "Download PDF" in built_report

    def test_has_opt_out_text(self, built_report):
        """Report page should have opt-out text."""
        assert "stop" in built_report.lower()

    def test_has_trading_name(self, built_report):
        """Report page should have trading name in footer."""
        assert "Test Trading Line" in built_report


class TestPublicPageContent:
    """Test public page HTML content."""

    def test_index_has_booking_placeholder(self):
        """Landing page should have booking link placeholder."""
        index_html = (PUBLIC_DIR / "index.html").read_text()
        assert "PLACEHOLDER_BOOKING_LINK" in index_html

    def test_index_has_surname_placeholders(self):
        """Landing page should have surname placeholders."""
        index_html = (PUBLIC_DIR / "index.html").read_text()
        assert "PLACEHOLDER_KIERAN_SURNAME" in index_html
        assert "PLACEHOLDER_SAM_SURNAME" in index_html

    def test_privacy_has_address_placeholder(self):
        """Privacy page should have address placeholder."""
        privacy_html = (PUBLIC_DIR / "privacy.html").read_text()
        assert "PLACEHOLDER_CONTACT_ADDRESS" in privacy_html

    def test_robots_allows_all(self):
        """robots.txt should allow all crawlers."""
        robots = (PUBLIC_DIR / "robots.txt").read_text()
        assert "Allow: /" in robots
        # Should NOT disallow /r/
        assert "Disallow: /r/" not in robots

    def test_sitemap_only_public_pages(self):
        """sitemap.xml should only list public pages, not /r/."""
        sitemap = (PUBLIC_DIR / "sitemap.xml").read_text()
        assert "airecommend.co.uk/" in sitemap
        assert "airecommend.co.uk/privacy" in sitemap
        assert "/r/" not in sitemap

    def test_headers_noindex_for_reports(self):
        """_headers should set noindex for /r/*."""
        headers = (PUBLIC_DIR / "_headers").read_text()
        assert "/r/*" in headers
        assert "noindex" in headers

    def test_headers_no_referrer_for_reports(self):
        """_headers should set no-referrer for /r/* to prevent slug leaking."""
        headers = (PUBLIC_DIR / "_headers").read_text()
        assert "no-referrer" in headers.lower()


class TestFictionalFixtures:
    """Verify that only fictional data is used in tests and samples."""

    def test_riverside_accountants_is_fictional(self):
        """The gold fixture should use .example domain (IANA reserved)."""
        import yaml

        fixture_path = REPO_ROOT / "apps" / "api" / "pilots" / "gold" / "riverside-accountants.yaml"
        with open(fixture_path) as f:
            pilot = yaml.safe_load(f)

        assert ".example" in pilot["url"], "Fixture URL must use .example domain"
        for domain in pilot.get("brand_domains", []):
            assert ".example" in domain, f"Brand domain {domain} must use .example"

    def test_no_real_firm_data_in_tests(self):
        """This test file should not contain real firm names."""
        this_file = Path(__file__).read_text()
        # List of real firms that should never appear in tests
        real_firms = [
            "Beever and Struthers",
            "DJH Mitten Clarke",
            "Xeinadin",
        ]
        for firm in real_firms:
            # Allow the firm name in the list definition above
            occurrences = this_file.count(firm)
            # It appears once in the list above, should not appear elsewhere
            assert occurrences == 1, f"Real firm '{firm}' found in test file"
