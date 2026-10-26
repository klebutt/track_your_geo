#!/usr/bin/env python3
"""AI Recommend static site builder.

Builds the site by copying public/ to dist/ and generating the sample report
from fictional fixtures. Optionally generates additional report pages from
vault manifest data.

Usage:
  python site/build.py                    # Build public pages + sample report
  python site/build.py --no-sample        # Skip sample report (not recommended)
  python site/build.py --vault PATH --batch wave2  # Also build from vault manifest

The sample report uses fictional data (riverside-accountants.example fixture)
and is required for the /sample-report.pdf link on the homepage.

The --vault option reads report data from the vault and generates /r/<slug>/
pages. It writes the slug mapping back to the vault (never to git).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import secrets
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

SITE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SITE_DIR.parent
PUBLIC_DIR = SITE_DIR / "public"
TEMPLATES_DIR = SITE_DIR / "templates"
DIST_DIR = SITE_DIR / "dist"

sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))


def load_config() -> dict:
    """Load site config, with fallbacks for missing values."""
    import importlib.util

    config_path = SITE_DIR / "config.py"
    try:
        spec = importlib.util.spec_from_file_location("site_config", config_path)
        if spec and spec.loader:
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            return {
                "booking_link": getattr(config_module, "BOOKING_LINK", "PLACEHOLDER_BOOKING_LINK"),
                "booking_link_raw": getattr(
                    config_module, "BOOKING_LINK_RAW",
                    "https://calendar.app.google/omsy1ZoJ7SsduLq87"
                ),
                "contact_address": getattr(config_module, "CONTACT_ADDRESS", ""),
                "contact_email": getattr(config_module, "CONTACT_EMAIL", "kieran@airecommend.co.uk"),
                "trading_name_line": getattr(config_module, "TRADING_NAME_LINE", "PLACEHOLDER_TRADING_NAME_LINE"),
            }
    except Exception:
        pass

    return {
        "booking_link": "PLACEHOLDER_BOOKING_LINK",
        "booking_link_raw": "https://calendar.app.google/omsy1ZoJ7SsduLq87",
        "contact_address": "PLACEHOLDER_CONTACT_ADDRESS",
        "contact_email": "kieran@airecommend.co.uk",
        "trading_name_line": "PLACEHOLDER_TRADING_NAME_LINE",
    }


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_slug() -> str:
    """Generate a 12-character URL-safe slug (~72 bits entropy)."""
    return secrets.token_urlsafe(9)


def _normalize_html_ampersands(html: str) -> str:
    """Escape bare & in HTML while leaving existing entities intact."""
    return re.sub(
        r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)",
        "&amp;",
        html,
    )


def _render_inline_markdown(text: str) -> str:
    """Render inline markdown (links, bold, italic) with HTML escaping."""
    if not text:
        return ""

    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    def split_links(s: str) -> str:
        out: list[str] = []
        pos = 0
        for m in link_pattern.finditer(s):
            if m.start() > pos:
                out.append(_render_inline_markdown_emphasis(s[pos : m.start()]))
            label = _render_inline_markdown_emphasis(m.group(1))
            href = escape_html(m.group(2).strip())
            out.append(f'<a href="{href}">{label}</a>')
            pos = m.end()
        if pos < len(s):
            out.append(_render_inline_markdown_emphasis(s[pos:]))
        return "".join(out)

    return split_links(text)


def _render_inline_markdown_emphasis(text: str) -> str:
    """Bold/italic on a segment with no link syntax."""
    parts: list[str] = []
    i = 0
    while i < len(text):
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                inner = _render_inline_markdown_emphasis(text[i + 2 : end])
                parts.append(f"<strong>{inner}</strong>")
                i = end + 2
                continue
        if text[i] == "*" and (i == 0 or text[i - 1] != "*"):
            end = i + 1
            while end < len(text):
                if text[end] == "*" and (end + 1 >= len(text) or text[end + 1] != "*"):
                    inner = escape_html(text[i + 1 : end])
                    parts.append(f"<em>{inner}</em>")
                    i = end + 1
                    break
                end += 1
            else:
                parts.append(escape_html(text[i]))
                i += 1
                continue
        parts.append(escape_html(text[i]))
        i += 1
    return "".join(parts)


def _markdown_to_html_fallback(md_text: str) -> str:
    """Convert customer-report markdown to HTML without the markdown package."""
    lines = md_text.split("\n")
    html_parts: list[str] = []
    list_open = False
    table_rows: list[list[str]] = []
    i = 0

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            html_parts.append("</ul>")
            list_open = False

    def flush_table() -> None:
        nonlocal table_rows
        if not table_rows:
            return
        while table_rows and all(not c.strip() for c in table_rows[0]):
            table_rows.pop(0)
        if not table_rows:
            return
        html_parts.append("<table>")
        for row_idx, row in enumerate(table_rows):
            tag = "th" if row_idx == 0 else "td"
            html_parts.append("<tr>")
            for cell in row:
                cell_html = _render_inline_markdown(cell.strip())
                html_parts.append(f"<{tag}>{cell_html}</{tag}>")
            html_parts.append("</tr>")
        html_parts.append("</table>")
        table_rows = []

    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("|") and "|" in line[1:]:
            close_list()
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.match(r"^[-:]+$", c) for c in cells):
                i += 1
                continue
            table_rows.append(cells)
            i += 1
            continue
        flush_table()

        if line.startswith("# "):
            close_list()
            html_parts.append(f"<h1>{_render_inline_markdown(line[2:])}</h1>")
        elif line.startswith("## "):
            close_list()
            html_parts.append(f"<h2>{_render_inline_markdown(line[3:])}</h2>")
        elif line.startswith("### "):
            close_list()
            html_parts.append(f"<h3>{_render_inline_markdown(line[4:])}</h3>")
        elif line.startswith("#### "):
            close_list()
            html_parts.append(f"<h4>{_render_inline_markdown(line[5:])}</h4>")
        elif line.startswith("> "):
            close_list()
            html_parts.append(f"<blockquote><p>{_render_inline_markdown(line[2:])}</p></blockquote>")
        elif re.match(r"^---+\s*$", line):
            close_list()
            html_parts.append("<hr />")
        elif line.startswith("- "):
            if not list_open:
                html_parts.append("<ul>")
                list_open = True
            html_parts.append(f"<li>{_render_inline_markdown(line[2:])}</li>")
        elif line.strip():
            close_list()
            html_parts.append(f"<p>{_render_inline_markdown(line)}</p>")
        else:
            close_list()
        i += 1

    flush_table()
    close_list()
    return "\n".join(html_parts)


def markdown_to_html(md_text: str) -> str:
    """Convert markdown to HTML (bold/italic, links, lists, tables, blockquotes)."""
    if HAS_MARKDOWN:
        html = markdown.markdown(
            md_text,
            extensions=["tables", "nl2br"],
        )
        return _normalize_html_ampersands(html)
    return _markdown_to_html_fallback(md_text)


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def copy_public_files(dist: Path, config: dict | None = None) -> None:
    """Copy all files from public/ to dist/ and generate dynamic redirects."""
    if dist.exists():
        shutil.rmtree(dist)
    shutil.copytree(PUBLIC_DIR, dist)
    print(f"Copied public/ to {dist}")

    # Generate _redirects file with booking URL from config
    if config and config.get("booking_link_raw"):
        redirects_content = f"""# Cloudflare Pages redirects
# https://developers.cloudflare.com/pages/configuration/redirects/

# Short booking URL -> Google Calendar appointment
/book {config['booking_link_raw']} 302
"""
        (dist / "_redirects").write_text(redirects_content, encoding="utf-8")
        print(f"Generated _redirects with /book -> {config['booking_link_raw']}")


def build_report_page(
    *,
    md_path: Path,
    pdf_path: Path,
    slug: str,
    dist: Path,
    config: dict,
    expected_sha256: str | None = None,
    run: dict | None = None,
) -> dict:
    """Build a single report page from markdown and PDF.

    Returns metadata dict with firm, slug, url, pdf_sha256, created.
    Raises ValueError if PDF hash doesn't match expected.
    """
    md_text = md_path.read_text(encoding="utf-8")

    # Extract firm name from markdown title
    firm_match = re.search(r"^# AI recommendation report - (.+)$", md_text, re.M)
    firm_name = firm_match.group(1) if firm_match else "Your firm"

    # Verify PDF hash if expected
    actual_sha256 = sha256_file(pdf_path)
    if expected_sha256 and actual_sha256 != expected_sha256:
        raise ValueError(
            f"PDF hash mismatch for {firm_name}: "
            f"expected {expected_sha256[:16]}..., got {actual_sha256[:16]}..."
        )

    # Create report directory
    report_dir = dist / "r" / slug
    report_dir.mkdir(parents=True, exist_ok=True)

    # Copy PDF (byte-for-byte)
    pdf_filename = pdf_path.name
    shutil.copy2(pdf_path, report_dir / pdf_filename)

    from tygeo.customer_web_report import (
        build_customer_report_body_html,
        load_web_run,
    )

    if run is None:
        run = load_web_run(md_path, md_text)
    report_html = build_customer_report_body_html(run)

    # Load and fill template
    template_path = TEMPLATES_DIR / "report.html"
    template = template_path.read_text(encoding="utf-8")

    html = (
        template.replace("{{FIRM_NAME}}", escape_html(firm_name))
        .replace("{{REPORT_CONTENT}}", report_html)
        .replace("{{PDF_FILENAME}}", pdf_filename)
        .replace("{{BOOKING_LINK}}", config["booking_link"])
        .replace("{{TRADING_NAME_LINE}}", escape_html(config["trading_name_line"]))
    )

    # Write index.html
    (report_dir / "index.html").write_text(html, encoding="utf-8")

    return {
        "firm": firm_name,
        "slug": slug,
        "url": f"https://airecommend.co.uk/r/{slug}/",
        "pdf_sha256": actual_sha256,
        "created": datetime.now(timezone.utc).isoformat(),
    }


def build_sample_report(dist: Path, config: dict) -> None:
    """Build a sample report page from the riverside-accountants fixture.

    The sample uses fictional data only and is labeled clearly as a sample.
    """
    from tygeo.customer_export import build_customer_markdown, write_customer_pdf

    # Load the gold fixture
    import yaml

    fixture_path = REPO_ROOT / "apps" / "api" / "pilots" / "gold" / "riverside-accountants.yaml"
    with open(fixture_path) as f:
        pilot = yaml.safe_load(f)

    # Create a fake run result for the sample with consistent data:
    # 2 of 5 brand mentions = 40% visibility (matches visibility_rate)
    queries = pilot["queries"]
    query_results = []
    for i, q in enumerate(queries):
        # Indices 0 and 2 get brand mentioned (2 of 5 = 40%)
        brand_mentioned = i in (0, 2)
        # Indices 1, 3, 4 show competitor instead
        competitors_mentioned = {}
        if not brand_mentioned and pilot["competitors"]:
            # Rotate through competitors for variety
            comp_idx = (i - 1) % len(pilot["competitors"])
            competitors_mentioned = {pilot["competitors"][comp_idx]: True}

        query_results.append({
            "query_text": q.replace("{location}", pilot["location"]),
            "brand_mentioned": brand_mentioned,
            "competitors_mentioned": competitors_mentioned,
        })

    sample_run = {
        "status": "completed",
        "brand_name": pilot["brand_name"],
        "model_name": "gpt-5-search-api,perplexity/sonar-pro,gemini/gemini-2.5-flash",
        "source_url": pilot["url"],
        "visibility_rate": 0.4,  # 2 of 5 = 40%
        "composite_score": 42.0,
        "profile_snapshot": {
            "location": pilot["location"],
            "source_url": pilot["url"],
            "services": pilot.get("services", []),
        },
        "query_results": query_results,
        # Sample banner for PDF/markdown (handled by customer_export._plain_from_run)
        "_sample_banner": (
            "SAMPLE REPORT - This uses fictional data for demonstration. "
            "Real reports show your firm's actual AI visibility."
        ),
    }

    # Generate markdown and PDF
    md_text = build_customer_markdown(sample_run)

    # Add SAMPLE label after the title (for HTML page)
    # The CTA is already correct via brand.py → plain_report.DEEPER_INSIGHTS_LEAD
    sample_label = (
        "\n\n> **SAMPLE REPORT** — This report uses fictional data for "
        "demonstration purposes. Real reports show your firm's actual AI visibility.\n"
    )
    if "# AI recommendation report" in md_text:
        md_text = md_text.replace(
            "# AI recommendation report",
            "# AI recommendation report" + sample_label,
            1
        )

    tmp_dir = dist / "_tmp_sample"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = tmp_dir / "sample-report.pdf"

    write_customer_pdf(sample_run, pdf_path, firm=pilot["brand_name"])

    md_path = tmp_dir / "sample-report.md"
    md_path.write_text(md_text, encoding="utf-8")

    # Build the sample report page
    build_report_page(
        md_path=md_path,
        pdf_path=pdf_path,
        slug="sample",
        dist=dist,
        config=config,
        run=sample_run,
    )

    # Copy PDF to root for landing page link
    shutil.copy2(pdf_path, dist / "sample-report.pdf")

    # Clean up temp
    shutil.rmtree(tmp_dir)

    print("Built sample report at /r/sample/")


def build_from_vault(
    vault_path: Path,
    batch: str,
    dist: Path,
    config: dict,
) -> list[dict]:
    """Build report pages from vault manifest.

    Reads <vault>/reports/<batch>-manifest.csv and generates pages
    for each firm with status=ok. Writes slug mapping to vault.

    Returns list of generated report metadata.
    """
    manifest_path = vault_path / "reports" / f"{batch}-manifest.csv"
    pdfs_dir = vault_path / "reports" / f"{batch}-pdfs"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    # Read existing links file to preserve slugs
    links_path = vault_path / "reports" / f"{batch}-links.csv"
    existing_slugs: dict[str, str] = {}
    if links_path.exists():
        with open(links_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("firm") and row.get("slug"):
                    existing_slugs[row["firm"]] = row["slug"]

    # Read manifest
    with open(manifest_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("status") == "ok"]

    if not rows:
        print(f"No successful reports in {manifest_path}")
        return []

    results = []
    for row in rows:
        firm = row["firm"]
        pdf_filename = Path(row.get("report_path", "")).name
        if not pdf_filename:
            print(f"  SKIP {firm}: no report_path")
            continue

        pdf_path = pdfs_dir / pdf_filename
        md_path = pdfs_dir / pdf_filename.replace(".pdf", ".md")

        if not pdf_path.exists():
            print(f"  SKIP {firm}: PDF not found at {pdf_path}")
            continue
        if not md_path.exists():
            print(f"  SKIP {firm}: markdown not found at {md_path}")
            continue

        # Use existing slug or generate new one
        slug = existing_slugs.get(firm) or generate_slug()

        try:
            meta = build_report_page(
                md_path=md_path,
                pdf_path=pdf_path,
                slug=slug,
                dist=dist,
                config=config,
            )
            results.append(meta)
            print(f"  OK {firm} -> /r/{slug}/")
        except Exception as e:
            print(f"  FAIL {firm}: {e}")

    # Write links file to vault (never to git)
    if results:
        links_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["firm", "slug", "url", "pdf_sha256", "created"]
        with open(links_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"Wrote {len(results)} links to {links_path}")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Build AI Recommend static site")
    parser.add_argument(
        "--no-sample",
        action="store_true",
        help="Skip building the sample report (sample is built by default)",
    )
    parser.add_argument(
        "--vault",
        type=Path,
        help="Path to vault for reading report data",
    )
    parser.add_argument(
        "--batch",
        default="wave2",
        help="Batch name (default: wave2)",
    )
    parser.add_argument(
        "--dist",
        type=Path,
        default=DIST_DIR,
        help=f"Output directory (default: {DIST_DIR})",
    )
    args = parser.parse_args()

    config = load_config()
    dist = args.dist.resolve()

    print(f"Building site to {dist}")
    copy_public_files(dist, config)

    # Build sample report by default (required for /sample-report.pdf link on homepage)
    if not args.no_sample:
        try:
            build_sample_report(dist, config)
        except Exception as e:
            print(f"WARNING: Could not build sample report: {e}")
            print("  (This is expected if fpdf2 or pyyaml is not installed)")

    if args.vault:
        vault = args.vault.resolve()
        print(f"Building reports from vault: {vault}")
        build_from_vault(vault, args.batch, dist, config)

    print("Build complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
