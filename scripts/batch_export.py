#!/usr/bin/env python3
"""Generic batch report exporter for AI Recommend.

Reads a CSV of firm_name,url pairs, runs 3-model probes via the local API,
exports PDF reports, and writes a manifest for site/build.py consumption.

Example:
  python scripts/batch_export.py --batch wave2 --input firms.csv
  python scripts/batch_export.py --batch wave2 --input firms.csv --dry-run

Output layout (in vault):
  reports/<batch>-manifest.csv   - manifest for site/build.py
  reports/<batch>-errors.csv     - failed/excluded firms
  reports/<batch>-progress.md    - live progress file
  reports/<batch>-pdfs/          - PDF and markdown files
  reports/<batch>-run-log.jsonl  - detailed per-firm log
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
API_ROOT = REPO / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from tygeo.customer_export import export_customer_report, pdf_filename_for_firm  # noqa: E402

DEFAULT_VAULT = Path(r"G:\My Drive\Obsidian\projects\track-your-geo")
USD_TO_GBP = 0.79
COST_PER_FIRM_USD = 0.65
MINUTES_PER_FIRM = 15.0

AUTH_HINTS = (
    "api key",
    "unauthorized",
    "authentication",
    "invalid_api_key",
    "incorrect api key",
    "OPENAI_API_KEY",
    "401",
    "403",
)

MANIFEST_FIELDS = [
    "firm",
    "url",
    "report_path",
    "generated_at",
    "run_cost_gbp",
    "sha256",
    "status",
]

ERROR_FIELDS = [
    "firm",
    "url",
    "exclusion_reason",
    "run_id",
    "generated_at",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_json(
    method: str, url: str, body: dict | None = None, timeout: float = 120
) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {url}: {detail[:500]}") from exc


def wait_run(
    base: str, run_id: int, *, poll_s: float = 20.0, max_wait_s: float = 60 * 90
) -> dict:
    deadline = time.time() + max_wait_s
    while time.time() < deadline:
        try:
            run = http_json("GET", f"{base}/api/runs/{run_id}", timeout=180)
        except (TimeoutError, urllib.error.URLError, OSError) as exc:
            print(f"  … run #{run_id} poll error ({exc}); retrying", flush=True)
            time.sleep(min(30, poll_s))
            continue
        status = run.get("status")
        if status in {"completed", "failed", "error"}:
            return run
        n = len(run.get("query_results") or [])
        print(f"  … run #{run_id} status={status} probes={n}", flush=True)
        time.sleep(poll_s)
    raise TimeoutError(f"Run {run_id} did not finish within {max_wait_s:.0f}s")


def is_auth_failure(message: str) -> bool:
    low = (message or "").lower()
    return any(h.lower() in low for h in AUTH_HINTS)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_progress(path: Path, batch: str, **kw) -> None:
    lines = [
        f"# {batch} batch progress",
        "",
        f"*Updated: {_now()}*",
        "",
        f"- **Done ok:** {kw.get('done_ok', 0)} / {kw.get('total', 0)}",
        f"- **Failed:** {kw.get('failed', 0)}",
        f"- **Skipped (reused):** {kw.get('skipped', 0)}",
        f"- **Current:** {kw.get('current', '—')}",
        f"- **Last:** {kw.get('last', '—')}",
        f"- **$ spent (USD):** ${kw.get('spent_usd', 0):.2f}",
        f"- **ETA remaining:** {kw.get('eta', 'n/a')}",
        "",
        f"PDFs: `reports/{batch}-pdfs/`",
        f"Manifest: `reports/{batch}-manifest.csv`",
        f"Errors: `reports/{batch}-errors.csv`",
        "",
    ]
    if kw.get("note"):
        lines.extend([kw["note"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def append_csv(path: Path, row: dict, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def load_jobs(path: Path) -> list[tuple[str, str]]:
    """Load firm_name,url pairs from CSV."""
    jobs: list[tuple[str, str]] = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            firm = (row.get("firm_name") or row.get("firm") or "").strip()
            url = (row.get("url") or "").strip()
            if firm and url.startswith("http"):
                jobs.append((firm, url))
    return jobs


def preflight_check(base_url: str) -> dict | None:
    """Check API health and return health dict, or None on failure."""
    try:
        health = http_json("GET", f"{base_url.rstrip('/')}/api/health", timeout=10)
        return health
    except Exception as exc:
        print(f"Preflight FAILED: local API not reachable at {base_url}", flush=True)
        print(f"  Error: {exc}", flush=True)
        return None


def run_batch(
    *,
    batch: str,
    jobs: list[tuple[str, str]],
    vault: Path,
    base_url: str,
    reuse_completed: bool,
    force: bool,
    dry_run: bool,
) -> int:
    """Run the batch export. Returns exit code."""
    out_dir = vault / "reports" / f"{batch}-pdfs"
    progress_path = vault / "reports" / f"{batch}-progress.md"
    manifest_path = vault / "reports" / f"{batch}-manifest.csv"
    errors_path = vault / "reports" / f"{batch}-errors.csv"
    jsonl_path = vault / "reports" / f"{batch}-run-log.jsonl"

    if dry_run:
        print(f"DRY RUN: would process {len(jobs)} firms", flush=True)
        print(f"  Output dir: {out_dir}", flush=True)
        print(f"  Manifest: {manifest_path}", flush=True)
        print(f"  Estimated cost: ${len(jobs) * COST_PER_FIRM_USD:.2f} USD", flush=True)
        print(f"  Estimated time: ~{len(jobs) * MINUTES_PER_FIRM:.0f} minutes", flush=True)
        print("\nFirms to process:", flush=True)
        for firm, url in jobs:
            pdf_name = pdf_filename_for_firm(firm)
            pdf_path = out_dir / pdf_name
            exists = pdf_path.exists() if out_dir.exists() else False
            skip = exists and reuse_completed and not force
            status = "SKIP (exists)" if skip else "QUEUE"
            print(f"  [{status}] {firm} ({url})", flush=True)
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(jobs)
    print(f"Batch '{batch}': {total} firms to process", flush=True)

    done_ok = 0
    failed = 0
    skipped = 0
    spent_usd = 0.0
    started = time.time()

    write_progress(
        progress_path,
        batch,
        done_ok=0,
        failed=0,
        skipped=0,
        total=total,
        current="(starting)",
        last="—",
        spent_usd=0.0,
        eta=f"~{total * MINUTES_PER_FIRM:.0f} min",
        note=f"Batch {batch} started.",
    )

    for idx, (firm, url) in enumerate(jobs, 1):
        pdf_name = pdf_filename_for_firm(firm)
        pdf_path = out_dir / pdf_name
        print(f"[{idx}/{total}] START {firm} · {url}", flush=True)

        write_progress(
            progress_path,
            batch,
            done_ok=done_ok,
            failed=failed,
            skipped=skipped,
            total=total,
            current=firm,
            last="in progress",
            spent_usd=spent_usd,
            eta=f"~{(total - idx + 1) * MINUTES_PER_FIRM:.0f} min",
        )

        if pdf_path.exists() and reuse_completed and not force:
            h = sha256_file(pdf_path)
            gen = datetime.fromtimestamp(pdf_path.stat().st_mtime, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            row = {
                "firm": firm,
                "url": url,
                "report_path": str(pdf_path),
                "generated_at": gen,
                "run_cost_gbp": "",
                "sha256": h,
                "status": "ok",
            }
            append_csv(manifest_path, row, MANIFEST_FIELDS)
            with jsonl_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({**row, "status": "reused_pdf"}, ensure_ascii=False) + "\n")
            skipped += 1
            done_ok += 1
            print(f"  SKIP existing PDF: {pdf_name}", flush=True)
            continue

        err_row = {
            "firm": firm,
            "url": url,
            "exclusion_reason": "",
            "run_id": "",
            "generated_at": _now(),
        }

        try:
            pending = http_json(
                "POST",
                f"{base_url.rstrip('/')}/api/runs/from-url",
                {"url": url, "vertical": "accountants"},
                timeout=180,
            )
            run_id = int(pending["id"])
            err_row["run_id"] = run_id
            print(f"  started run #{run_id}", flush=True)

            run = wait_run(base_url.rstrip("/"), run_id)
            if run.get("status") != "completed":
                reason = f"run_status={run.get('status')}"
                err_row["exclusion_reason"] = reason
                if is_auth_failure(json.dumps(run) + reason):
                    append_csv(errors_path, err_row, ERROR_FIELDS)
                    print(f"FATAL auth: {reason}", flush=True)
                    return 3
                append_csv(errors_path, err_row, ERROR_FIELDS)
                with jsonl_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({**err_row, "status": "failed"}, ensure_ascii=False) + "\n")
                failed += 1
                print(f"  FAIL {firm}: {reason}", flush=True)
                continue

            cost_usd = float(run.get("total_cost_usd") or 0.0)
            spent_usd += cost_usd

            meta = export_customer_report(run, out_dir)
            pdf = Path(meta["pdf_path"])
            h = sha256_file(pdf)
            row = {
                "firm": meta.get("firm") or firm,
                "url": url,
                "report_path": str(pdf),
                "generated_at": _now(),
                "run_cost_gbp": round(cost_usd * USD_TO_GBP, 4),
                "sha256": h,
                "status": "ok",
            }
            append_csv(manifest_path, row, MANIFEST_FIELDS)
            with jsonl_path.open("a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {**row, "run_id": run_id, "run_cost_usd": round(cost_usd, 4)},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            done_ok += 1
            elapsed = time.time() - started
            avg = elapsed / max(done_ok - skipped, 1)
            remaining = (total - idx) * (avg / 60.0)
            print(
                f"  FINISH {row['firm']} · ${cost_usd:.2f} · "
                f"spent ${spent_usd:.2f} · remaining ~{remaining:.0f} min · sha={h[:12]}…",
                flush=True,
            )
            write_progress(
                progress_path,
                batch,
                done_ok=done_ok,
                failed=failed,
                skipped=skipped,
                total=total,
                current="(idle)",
                last=f"ok · {row['firm']}",
                spent_usd=spent_usd,
                eta=f"~{remaining:.0f} min",
            )

        except Exception as exc:
            reason = str(exc)[:400]
            err_row["exclusion_reason"] = reason
            append_csv(errors_path, err_row, ERROR_FIELDS)
            with jsonl_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({**err_row, "status": "failed"}, ensure_ascii=False) + "\n")
            failed += 1
            print(f"  FAIL {firm}: {reason}", flush=True)

            if is_auth_failure(reason):
                write_progress(
                    progress_path,
                    batch,
                    done_ok=done_ok,
                    failed=failed,
                    skipped=skipped,
                    total=total,
                    current="STOPPED",
                    last=f"auth fail · {firm}",
                    spent_usd=spent_usd,
                    eta="n/a",
                    note=f"Hard stop: {reason}",
                )
                return 3

            write_progress(
                progress_path,
                batch,
                done_ok=done_ok,
                failed=failed,
                skipped=skipped,
                total=total,
                current="(idle)",
                last=f"fail · {firm}",
                spent_usd=spent_usd,
                eta=f"~{(total - idx) * MINUTES_PER_FIRM:.0f} min",
                note=f"Excluded: {reason[:200]}",
            )

    write_progress(
        progress_path,
        batch,
        done_ok=done_ok,
        failed=failed,
        skipped=skipped,
        total=total,
        current="(complete)",
        last="batch finished",
        spent_usd=spent_usd,
        eta="0 min",
        note=f"Final: {done_ok} ok ({skipped} reused) · {failed} failed · ${spent_usd:.2f} USD",
    )
    print(
        f"Done. {done_ok}/{total} ok ({skipped} reused) · {failed} failed · ${spent_usd:.2f} · "
        f"manifest {manifest_path}",
        flush=True,
    )
    return 0 if failed == 0 or done_ok > 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generic batch report exporter for AI Recommend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  # Dry run to see what would happen
  python scripts/batch_export.py --batch wave2 --input firms.csv --dry-run

  # Run full batch
  python scripts/batch_export.py --batch wave2 --input firms.csv

  # Resume with existing PDFs reused
  python scripts/batch_export.py --batch wave2 --input firms.csv --reuse-completed

Input CSV format:
  firm_name,url
  "Example Accountants Ltd","https://example-accountants.co.uk"
  "Test & Partners","https://testandpartners.example"
""",
    )
    ap.add_argument(
        "--batch",
        required=True,
        help="Batch name (e.g. wave2). Determines output folder names.",
    )
    ap.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to CSV with firm_name,url columns",
    )
    ap.add_argument(
        "--vault",
        type=Path,
        default=DEFAULT_VAULT,
        help=f"Vault path (default: {DEFAULT_VAULT})",
    )
    ap.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Local API base URL (default: http://127.0.0.1:8000)",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max firms to process (default: all)",
    )
    ap.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip first N firms (default: 0)",
    )
    ap.add_argument(
        "--reuse-completed",
        action="store_true",
        default=True,
        help="Skip firms with existing PDFs (default: True)",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if PDF exists",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without running probes",
    )
    args = ap.parse_args()

    if not args.input.exists():
        print(f"ERROR: Input CSV not found: {args.input}", flush=True)
        return 2

    jobs = load_jobs(args.input)
    if not jobs:
        print(f"ERROR: No valid firm_name,url rows in {args.input}", flush=True)
        return 2

    batch_jobs = jobs[args.offset :]
    if args.limit:
        batch_jobs = batch_jobs[: args.limit]

    if not batch_jobs:
        print("ERROR: No jobs after applying offset/limit", flush=True)
        return 2

    print(f"Loaded {len(jobs)} firms from {args.input}", flush=True)
    print(f"After offset={args.offset}, limit={args.limit}: {len(batch_jobs)} to process", flush=True)
    print(f"Estimated cost: ~${len(batch_jobs) * COST_PER_FIRM_USD:.2f} USD", flush=True)
    print(f"Estimated time: ~{len(batch_jobs) * MINUTES_PER_FIRM:.0f} minutes", flush=True)
    print("", flush=True)

    if not args.dry_run:
        health = preflight_check(args.base_url)
        if health is None:
            print("", flush=True)
            print("To start the local API:", flush=True)
            print("  .\\tygeo-venv\\Scripts\\uvicorn.exe tygeo.main:app --host 127.0.0.1 --port 8000", flush=True)
            return 2
        print(f"API health: {health}", flush=True)
        print("", flush=True)

    return run_batch(
        batch=args.batch,
        jobs=batch_jobs,
        vault=args.vault,
        base_url=args.base_url,
        reuse_completed=args.reuse_completed,
        force=args.force,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
