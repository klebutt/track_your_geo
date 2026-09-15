"""Wave-1 batch of 40 cosmetics PDFs (after QA-10). Vault URL list only — not git.

Outputs cosmetics-schema manifest + errors file. Does not regenerate QA-10 PDFs
unless --force. Skips existing PDF for a firm when --reuse-completed.

Example:
  .\\tygeo-venv\\Scripts\\python.exe scripts\\wave1_batch40_export.py --skip-pause
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
    "firm_name",
    "url",
    "report_path",
    "generated_at",
    "run_cost_gbp",
    "sha256",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_json(method: str, url: str, body: dict | None = None, timeout: float = 120) -> dict:
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


def wait_run(base: str, run_id: int, *, poll_s: float = 20.0, max_wait_s: float = 60 * 90) -> dict:
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


def write_progress(path: Path, **kw) -> None:
    lines = [
        "# Wave-1 batch-40 progress",
        "",
        f"*Updated: {_now()}*",
        "",
        f"- **Done ok:** {kw.get('done_ok', 0)} / {kw.get('total', 0)}",
        f"- **Failed:** {kw.get('failed', 0)}",
        f"- **Current:** {kw.get('current', '—')}",
        f"- **Last:** {kw.get('last', '—')}",
        f"- **$ spent (USD):** ${kw.get('spent_usd', 0):.2f}",
        f"- **ETA remaining:** {kw.get('eta', 'n/a')}",
        "",
        "PDFs: `reports/wave1-pdfs/`",
        "Manifest: `reports/wave1-batch40-manifest.csv`",
        "Errors: `reports/wave1-batch40-errors.csv`",
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
    jobs: list[tuple[str, str]] = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            firm = (row.get("firm_name") or "").strip()
            url = (row.get("url") or "").strip()
            if firm and url.startswith("http"):
                jobs.append((firm, url))
    return jobs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    ap.add_argument(
        "--urls-csv",
        type=Path,
        default=None,
        help="Default: <vault>/reports/wave1-batch40-urls.csv",
    )
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--reuse-completed", action="store_true", default=True)
    ap.add_argument("--force", action="store_true", help="Regenerate even if PDF exists")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    vault: Path = args.vault
    urls_csv = args.urls_csv or (vault / "reports" / "wave1-batch40-urls.csv")
    out_dir = vault / "reports" / "wave1-pdfs"
    progress_path = vault / "reports" / "wave1-batch40-progress.md"
    manifest_path = vault / "reports" / "wave1-batch40-manifest.csv"
    errors_path = vault / "reports" / "wave1-batch40-errors.csv"
    jsonl_path = vault / "reports" / "wave1-batch40-run-log.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = load_jobs(urls_csv)
    batch = jobs[args.offset : args.offset + args.limit]
    total = len(batch)
    print(f"Loaded {len(jobs)} jobs; batch size {total}", flush=True)

    try:
        health = http_json("GET", f"{args.base_url.rstrip('/')}/api/health", timeout=10)
        print(f"API health: {health}", flush=True)
    except Exception as exc:
        print(f"FATAL: local API not reachable: {exc}", flush=True)
        return 2

    done_ok = 0
    failed = 0
    spent_usd = 0.0
    started = time.time()
    per_firm_min = 15.0

    write_progress(
        progress_path,
        done_ok=0,
        failed=0,
        total=total,
        current="(starting)",
        last="—",
        spent_usd=0.0,
        eta=f"~{total * per_firm_min:.0f} min",
        note="Batch-40 started. QA-10 not regenerated.",
    )

    for idx, (firm, url) in enumerate(batch, 1):
        pdf_name = pdf_filename_for_firm(firm)
        pdf_path = out_dir / pdf_name
        print(f"[{idx}/{total}] START {firm} · {url}", flush=True)
        write_progress(
            progress_path,
            done_ok=done_ok,
            failed=failed,
            total=total,
            current=firm,
            last="in progress",
            spent_usd=spent_usd,
            eta=f"~{(total - idx + 1) * per_firm_min:.0f} min",
        )

        if pdf_path.exists() and args.reuse_completed and not args.force:
            # Do not re-GEO; hash existing PDF (should not hit QA-10 names in this list)
            h = sha256_file(pdf_path)
            gen = datetime.fromtimestamp(pdf_path.stat().st_mtime, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            row = {
                "firm_name": firm,
                "url": url,
                "report_path": str(pdf_path),
                "generated_at": gen,
                "run_cost_gbp": "",
                "sha256": h,
            }
            append_csv(manifest_path, row, MANIFEST_FIELDS)
            with jsonl_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({**row, "status": "reused_pdf"}, ensure_ascii=False) + "\n")
            done_ok += 1
            print(f"  SKIP existing PDF: {pdf_name}", flush=True)
            continue

        err_row = {
            "firm_name": firm,
            "url": url,
            "exclusion_reason": "",
            "run_id": "",
            "generated_at": _now(),
        }

        try:
            pending = http_json(
                "POST",
                f"{args.base_url.rstrip('/')}/api/runs/from-url",
                {"url": url, "vertical": "accountants"},
                timeout=180,
            )
            run_id = int(pending["id"])
            err_row["run_id"] = run_id
            print(f"  started run #{run_id}", flush=True)
            run = wait_run(args.base_url.rstrip("/"), run_id)
            if run.get("status") != "completed":
                reason = f"run_status={run.get('status')}"
                err_row["exclusion_reason"] = reason
                if is_auth_failure(json.dumps(run) + reason):
                    append_csv(
                        errors_path,
                        err_row,
                        ["firm_name", "url", "exclusion_reason", "run_id", "generated_at"],
                    )
                    print(f"FATAL auth: {reason}", flush=True)
                    return 3
                append_csv(
                    errors_path,
                    err_row,
                    ["firm_name", "url", "exclusion_reason", "run_id", "generated_at"],
                )
                with jsonl_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({**err_row, "status": "failed"}, ensure_ascii=False) + "\n")
                failed += 1
                print(f"  FAIL {firm}: {reason}", flush=True)
                continue

            cost_usd = float(run.get("total_cost_usd") or 0.0)
            spent_usd += cost_usd
            # Prefer inferred brand from run for filename consistency with export
            meta = export_customer_report(run, out_dir)
            pdf = Path(meta["pdf_path"])
            h = sha256_file(pdf)
            row = {
                "firm_name": meta.get("firm") or firm,
                "url": url,
                "report_path": str(pdf),
                "generated_at": _now(),
                "run_cost_gbp": round(cost_usd * USD_TO_GBP, 4),
                "sha256": h,
            }
            append_csv(manifest_path, row, MANIFEST_FIELDS)
            with jsonl_path.open("a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {**row, "status": "ok", "run_id": run_id, "run_cost_usd": round(cost_usd, 4)},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            done_ok += 1
            elapsed = time.time() - started
            avg = elapsed / max(done_ok, 1)
            remaining = (total - idx) * (avg / 60.0)
            print(
                f"  FINISH {row['firm_name']} · ${cost_usd:.2f} · "
                f"spent ${spent_usd:.2f} · remaining ~{remaining:.0f} min · sha={h[:12]}…",
                flush=True,
            )
            write_progress(
                progress_path,
                done_ok=done_ok,
                failed=failed,
                total=total,
                current="(idle)",
                last=f"ok · {row['firm_name']}",
                spent_usd=spent_usd,
                eta=f"~{remaining:.0f} min",
            )

        except Exception as exc:
            reason = str(exc)[:400]
            err_row["exclusion_reason"] = reason
            append_csv(
                errors_path,
                err_row,
                ["firm_name", "url", "exclusion_reason", "run_id", "generated_at"],
            )
            with jsonl_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({**err_row, "status": "failed"}, ensure_ascii=False) + "\n")
            failed += 1
            print(f"  FAIL {firm}: {reason}", flush=True)
            if is_auth_failure(reason):
                write_progress(
                    progress_path,
                    done_ok=done_ok,
                    failed=failed,
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
                done_ok=done_ok,
                failed=failed,
                total=total,
                current="(idle)",
                last=f"fail · {firm}",
                spent_usd=spent_usd,
                eta=f"~{(total - idx) * per_firm_min:.0f} min",
                note=f"Excluded: {reason[:200]}",
            )

    write_progress(
        progress_path,
        done_ok=done_ok,
        failed=failed,
        total=total,
        current="(complete)",
        last="batch finished",
        spent_usd=spent_usd,
        eta="0 min",
        note=f"Final: {done_ok} ok · {failed} failed · ${spent_usd:.2f} USD",
    )
    print(
        f"Done. {done_ok}/{total} ok · {failed} failed · ${spent_usd:.2f} · "
        f"manifest {manifest_path}",
        flush=True,
    )
    return 0 if failed == 0 or done_ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
