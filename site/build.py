#!/usr/bin/env python3
"""AI Recommend static site builder.

Builds the site by copying public/ to dist/ and optionally generating
report pages from vault manifest data.

Usage:
  python site/build.py                    # Build public pages only
  python site/build.py --sample           # Include sample report from fixtures
  python site/build.py --vault PATH --batch wave2  # Build from vault manifest

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
    try:
        from site.config import (
            BOOKING_LINK,
            CONTACT_ADDRESS,
            CONTACT_EMAIL,
            TRADING_NAME_LINE,
        )
        return {
            "booking_link": BOOKING_LINK,
            "contact_address": CONTACT_ADDRESS,
            "contact_email": CONTACT_EMAIL,
            "trading_name_line": TRADING_NAME_LINE,
        }
    except ImportError:
        return {
            "booking_link": "PLACEHOLDER_BOOKING_LINK",
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


def markdown_to_html(md_text: str) -> str:
    """Convert markdown to HTML, with fallback if markdown library missing."""
    if HAS_MARKDOWN:
        return markdown.markdown(md_text, extensions=["tables"])
    # Basic fallback conversion
    html_lines = []
    for line in md_text.split("\n"):
        line = line.rstrip()
        if line.startswith("# "):
            html_lines.append(f"<h1>{escape_html(line[2:])}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{escape_html(line[3:])}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{escape_html(line[4:])}</h3>")
        elif line.startswith("#### "):
            html_lines.append(f"<h4>{escape_html(line[5:])}</h4>")
        elif line.startswith("- "):
            html_lines.append(f"<li>{escape_html(line[2:])}</li>")
        elif line.startswith("|"):
            continue  # Skip table rows in fallback
        elif line.strip():
            html_lines.append(f"<p>{escape_html(line)}</p>")
    return "\n".join(html_lines)


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def copy_public_files(dist: Path) -> None:
    """Copy all files from public/ to dist/."""
    if dist.exists():
        shutil.rmtree(dist)
    shutil.copytree(PUBLIC_DIR, dist)
    print(f"Copied public/ to {dist}")


def build_report_page(
    *,
    md_path: Path,
    pdf_path: Path,
    slug: str,
    dist: Path,
    config: dict,
    expected_sha256: str | None = None,
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

    # Convert markdown to HTML
    report_html = markdown_to_html(md_text)

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
    """Build a sample report page from the riverside-accountants fixture."""
    from tygeo.customer_export import build_customer_markdown, write_customer_pdf

    # Load the gold fixture
    import yaml

    fixture_path = REPO_ROOT / "apps" / "api" / "pilots" / "gold" / "riverside-accountants.yaml"
    with open(fixture_path) as f:
        pilot = yaml.safe_load(f)

    # Create a fake run result for the sample
    sample_run = {
        "status": "completed",
        "brand_name": pilot["brand_name"],
        "model_name": "gpt-5-search-api,perplexity/sonar-pro,gemini/gemini-2.5-flash",
        "source_url": pilot["url"],
        "visibility_rate": 0.4,
        "composite_score": 45.2,
        "profile_snapshot": {
            "location": pilot["location"],
            "source_url": pilot["url"],
            "services": pilot.get("services", []),
        },
        "query_results": [
            {
                "query_text": q.replace("{location}", pilot["location"]),
                "brand_mentioned": i % 2 == 0,
                "competitors_mentioned": (
                    {pilot["competitors"][0]: True} if i % 2 != 0 else {}
                ),
            }
            for i, q in enumerate(pilot["queries"])
        ],
    }

    # Generate markdown and PDF
    md_text = build_customer_markdown(sample_run)
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
        "--sample",
        action="store_true",
        help="Include sample report from fixtures",
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
    copy_public_files(dist)

    if args.sample:
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
