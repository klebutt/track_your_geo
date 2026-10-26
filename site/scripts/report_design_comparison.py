#!/usr/bin/env python3
"""Capture before/after/PDF screenshots for report page design review (fictional data only)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = Path("/opt/cursor/artifacts/screenshots")
OLD_SHA = "567deba"  # main after PR #14 (pre design parity)


def _page_screenshot(url: str, out: Path, width: int) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    shot = shutil.which("shot-scraper") or str(Path.home() / ".local/bin/shot-scraper")
    subprocess.run(
        [shot, url, "-o", str(out), "-w", str(width), "--wait", "500"],
        check=True,
        capture_output=True,
        timeout=60,
    )


def _pdf_page1_png(pdf: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    page = doc.get_page(0)
    bitmap = page.render(scale=2)
    bitmap.to_pil().save(out)
    doc.close()


def _fictional_runs() -> dict[str, dict]:
    base_queries = [
        "Best accountants in Example Town, UK?",
        "Small business accountant Example Town",
        "VAT accountant near Example Town",
        "Payroll services Example Town",
        "Year end accounts Example Town",
        "Tax planning Example Town",
        "Bookkeeping Example Town",
        "Startup accountant Example Town",
        "Charity accountant Example Town",
        "Online accountants UK",
    ]
    competitors = ["Fictional Rival LLP", "Example & Co Accountants"]

    def run(wins: int, label: str) -> dict:
        qrs = []
        for i, q in enumerate(base_queries):
            if i < wins:
                qrs.append(
                    {
                        "query_text": q,
                        "brand_mentioned": True,
                        "competitors_mentioned": {},
                    }
                )
            elif i < wins + 2:
                qrs.append(
                    {
                        "query_text": q,
                        "brand_mentioned": False,
                        "competitors_mentioned": {competitors[i % 2]: True},
                    }
                )
            else:
                qrs.append(
                    {
                        "query_text": q,
                        "brand_mentioned": False,
                        "competitors_mentioned": {},
                    }
                )
        vis = wins / max(len(base_queries), 1)
        return {
            "status": "completed",
            "brand_name": label,
            "model_name": "gpt-5-search-api,perplexity/sonar-pro,gemini/gemini-2.5-flash",
            "source_url": "https://fictional-firm.example/",
            "visibility_rate": vis,
            "composite_score": 18.0 + wins * 7.5,
            "profile_snapshot": {
                "location": "Example Town, UK",
                "services": ["Tax", "Payroll", "VAT"],
            },
            "query_results": qrs,
        }

    return {
        "low": run(1, "Fictional Low Score Ltd"),
        "high": run(8, "Fictional High Score Ltd"),
    }


def _export_bundle(run: dict, out_dir: Path) -> tuple[Path, Path]:
    sys.path.insert(0, str(REPO / "apps" / "api"))
    from tygeo.customer_export import export_customer_report

    out_dir.mkdir(parents=True, exist_ok=True)
    meta = export_customer_report(run, out_dir)
    return Path(meta["pdf_path"]), Path(meta["md_path"])


def _build_pages(dist: Path, repo: Path, bundles: dict[str, tuple[Path, Path]], sample: bool) -> None:
    """Build dist using site/build from repo in a fresh Python process (no import cache bleed)."""
    if dist.exists():
        shutil.rmtree(dist)
    bundles_json = {
        slug: [str(md.resolve()), str(pdf.resolve())]
        for slug, (md, pdf) in bundles.items()
    }
    helper = REPO / "site/scripts/build_comparison_dist.py"
    cmd = [
        sys.executable,
        str(helper),
        "--repo-root",
        str(repo.resolve()),
        "--dist",
        str(dist.resolve()),
        "--bundles",
        json.dumps(bundles_json),
    ]
    if sample:
        cmd.append("--sample")
    subprocess.run(cmd, check=True, cwd=str(repo.resolve()))


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    tmp = Path("/tmp/report-design-compare")
    old_repo = tmp / "old-repo"
    if old_repo.exists() or (tmp / ".git").exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(old_repo)],
            cwd=REPO,
            capture_output=True,
        )
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()

    bundles_dir = tmp / "bundles"
    fictional = _fictional_runs()
    bundle_paths: dict[str, tuple[Path, Path]] = {}
    pdf_paths: dict[str, Path] = {}

    for key, run in fictional.items():
        pdf, md = _export_bundle(run, bundles_dir / key)
        bundle_paths[key] = (md, pdf)
        pdf_paths[key] = pdf

    # Sample PDF from current repo
    sys.path.insert(0, str(REPO / "apps" / "api"))
    dist_sample = tmp / "dist-new"
    _build_pages(dist_sample, REPO, bundle_paths, sample=True)
    sample_pdfs = list((dist_sample / "r" / "sample").glob("*.pdf"))
    pdf_paths["sample"] = sample_pdfs[0]

    # Old design at pinned SHA
    subprocess.run(["git", "worktree", "add", "--detach", str(old_repo), OLD_SHA], cwd=REPO, check=True)
    dist_old = tmp / "dist-old"
    _build_pages(dist_old, old_repo, bundle_paths, sample=True)

    scenarios = ["sample", "low", "high"]
    widths = {"desktop": 1280, "mobile": 390}

    import threading

    def serve(directory: Path, port: int) -> ThreadingHTTPServer:
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(directory), **kwargs)

        httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        return httpd

    http_old = serve(dist_old, 8765)
    http_new = serve(dist_sample, 8766)
    time.sleep(0.3)

    for scenario in scenarios:
        slug = "sample" if scenario == "sample" else scenario
        for label, port in ("before", 8765), ("after", 8766):
            for width_name, w in widths.items():
                url = f"http://127.0.0.1:{port}/r/{slug}/index.html"
                out = ARTIFACTS / f"report-{scenario}-{label}-{width_name}.png"
                _page_screenshot(url, out, w)
                print(f"Wrote {out}")
        pdf_out = ARTIFACTS / f"report-{scenario}-pdf-page1.png"
        _pdf_page1_png(pdf_paths[scenario], pdf_out)
        print(f"Wrote {pdf_out}")

    http_old.shutdown()
    http_new.shutdown()
    subprocess.run(["git", "worktree", "remove", "--force", str(old_repo)], cwd=REPO, check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
