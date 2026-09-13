"""Wave-1 bulk URL→report → customer PDF for vault handoff.

Reads prospect URLs from a vault markdown path (never copies the list into git).
Writes PDFs, JSONL/CSV log, and live progress into the vault.

Example:
  .\\tygeo-venv\\Scripts\\python.exe scripts\\wave1_bulk_export.py ^
    --vault "G:\\My Drive\\Obsidian\\projects\\track-your-geo" ^
    --limit 50 --pause-after 5
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Allow importing tygeo from apps/api when run as a script
REPO = Path(__file__).resolve().parents[1]
API_ROOT = REPO / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from tygeo.customer_export import export_customer_report, pdf_filename_for_firm  # noqa: E402

DEFAULT_VAULT = Path(r"G:\My Drive\Obsidian\projects\track-your-geo")
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


@dataclass
class Prospect:
    firm: str
    url: str
    location: str


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_prospects(path: Path) -> list[Prospect]:
    """Parse full-list table rows from accountant-prospects.md."""
    text = path.read_text(encoding="utf-8")
    # Prefer ## Full list section if present
    full = text
    m = re.search(r"## Full list\s*(.*?)(?:\n## |\Z)", text, flags=re.S | re.I)
    if m:
        full = m.group(1)
    prospects: list[Prospect] = []
    seen: set[str] = set()
    for line in full.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        firm, url, location = cells[0], cells[1], cells[2]
        if firm.lower() in {"firm name", "---"} or "---" in firm:
            continue
        if not url.startswith("http"):
            continue
        key = url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        prospects.append(Prospect(firm=firm, url=url, location=location))
    return prospects


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


def wait_run(base: str, run_id: int, *, poll_s: float = 15.0, max_wait_s: float = 60 * 45) -> dict:
    deadline = time.time() + max_wait_s
    while time.time() < deadline:
        run = http_json("GET", f"{base}/api/runs/{run_id}", timeout=60)
        status = run.get("status")
        if status in {"completed", "failed", "error"}:
            return run
        print(f"  … run #{run_id} status={status}", flush=True)
        time.sleep(poll_s)
    raise TimeoutError(f"Run {run_id} did not finish within {max_wait_s:.0f}s")


def is_auth_failure(message: str) -> bool:
    low = (message or "").lower()
    return any(h.lower() in low for h in AUTH_HINTS)


def write_progress(
    path: Path,
    *,
    done: int,
    total: int,
    current: str,
    last: str,
    spent: float,
    eta_min: float | None,
    note: str = "",
) -> None:
    eta_s = f"~{eta_min:.0f} min" if eta_min is not None else "n/a"
    lines = [
        "# Wave-1 bulk progress",
        "",
        f"*Updated: {_now()}*",
        "",
        f"- **Done:** {done} / {total}",
        f"- **Current:** {current}",
        f"- **Last:** {last}",
        f"- **$ spent so far:** ${spent:.2f}",
        f"- **ETA remaining:** {eta_s}",
        "",
    ]
    if note:
        lines.extend([note, ""])
    lines.extend(
        [
            "PDFs: `reports/wave1-pdfs/`",
            "Run log: `reports/wave1-run-log.jsonl` + `reports/wave1-manifest.csv`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_csv(path: Path, row: dict, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def maybe_touch_status(vault: Path, *, done: int, total: int, force: bool = False) -> None:
    if not force and done % 5 != 0:
        return
    status = vault / "status.md"
    if not status.exists():
        return
    text = status.read_text(encoding="utf-8")
    stamp = f"Wave-1 bulk: {done}/{total} firms · {_now()}"
    marker = "<!-- wave1-bulk-progress -->"
    block = f"{marker}\n- {stamp}\n"
    if marker in text:
        text = re.sub(
            rf"{re.escape(marker)}\n-.*\n",
            block,
            text,
            count=1,
        )
    else:
        # Insert under checklist if present
        if "## Checklist for next session" in text:
            text = text.replace(
                "## Checklist for next session",
                f"## Checklist for next session\n\n{block}",
                1,
            )
        else:
            text = text.rstrip() + "\n\n" + block + "\n"
    status.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Wave-1 bulk customer PDF export")
    ap.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    ap.add_argument(
        "--prospects",
        type=Path,
        default=None,
        help="Default: <vault>/accountant-prospects.md",
    )
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--pause-after", type=int, default=5)
    ap.add_argument("--skip-pause", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="Parse prospects only")
    ap.add_argument(
        "--reuse-completed",
        action="store_true",
        help="Skip firms whose PDF already exists in wave1-pdfs",
    )
    args = ap.parse_args()

    vault: Path = args.vault
    prospects_path = args.prospects or (vault / "accountant-prospects.md")
    out_dir = vault / "reports" / "wave1-pdfs"
    progress_path = vault / "reports" / "wave1-progress.md"
    jsonl_path = vault / "reports" / "wave1-run-log.jsonl"
    csv_path = vault / "reports" / "wave1-manifest.csv"
    out_dir.mkdir(parents=True, exist_ok=True)

    prospects = parse_prospects(prospects_path)
    batch = prospects[args.offset : args.offset + args.limit]
    total = len(batch)
    print(f"Loaded {len(prospects)} prospects; batch size {total} (offset={args.offset})", flush=True)
    if args.dry_run:
        for i, p in enumerate(batch, 1):
            print(f"{i:02d}. {p.firm} | {p.location} | {p.url}")
        return 0

    # Health check
    try:
        health = http_json("GET", f"{args.base_url.rstrip('/')}/api/health", timeout=10)
        print(f"API health: {health}", flush=True)
    except Exception as exc:
        print(f"FATAL: local API not reachable at {args.base_url}: {exc}", flush=True)
        return 2

    fields = [
        "firm",
        "url",
        "location",
        "recommend_x",
        "recommend_n",
        "report_path",
        "run_id",
        "run_cost_usd",
        "generated_at",
        "status",
        "exclusion_reason",
    ]

    done_ok = 0
    spent = 0.0
    started = time.time()
    per_firm_min = 15.0  # planning estimate

    write_progress(
        progress_path,
        done=0,
        total=total,
        current="(starting)",
        last="—",
        spent=0.0,
        eta_min=total * per_firm_min,
        note="Batch started.",
    )

    for idx, p in enumerate(batch, 1):
        pdf_name = pdf_filename_for_firm(p.firm)
        pdf_path = out_dir / pdf_name
        if args.reuse_completed and pdf_path.exists():
            print(f"[{idx}/{total}] SKIP existing PDF: {pdf_name}", flush=True)
            done_ok += 1
            continue

        print(f"[{idx}/{total}] START {p.firm} · {p.url}", flush=True)
        write_progress(
            progress_path,
            done=done_ok,
            total=total,
            current=p.firm,
            last="in progress",
            spent=spent,
            eta_min=(total - idx + 1) * per_firm_min,
        )

        row = {
            "firm": p.firm,
            "url": p.url,
            "location": p.location,
            "recommend_x": "",
            "recommend_n": "",
            "report_path": "",
            "run_id": "",
            "run_cost_usd": "",
            "generated_at": _now(),
            "status": "failed",
            "exclusion_reason": "",
        }

        try:
            pending = http_json(
                "POST",
                f"{args.base_url.rstrip('/')}/api/runs/from-url",
                {"url": p.url, "vertical": "accountants"},
                timeout=120,
            )
            run_id = int(pending["id"])
            row["run_id"] = run_id
            print(f"  started run #{run_id}", flush=True)
            run = wait_run(args.base_url.rstrip("/"), run_id)
            if run.get("status") != "completed":
                reason = f"run_status={run.get('status')}"
                row["exclusion_reason"] = reason
                if is_auth_failure(json.dumps(run)):
                    print(f"FATAL auth/provider: {reason}", flush=True)
                    append_jsonl(jsonl_path, row)
                    append_csv(csv_path, row, fields)
                    maybe_touch_status(vault, done=done_ok, total=total, force=True)
                    return 3
                print(f"  FAIL {p.firm}: {reason}", flush=True)
            else:
                cost = float(run.get("total_cost_usd") or 0.0)
                spent += cost
                pr = run.get("plain_report") or {}
                meta = export_customer_report(run, out_dir)
                row.update(
                    {
                        "recommend_x": pr.get("searches_recommended", ""),
                        "recommend_n": pr.get("searches_total", ""),
                        "report_path": meta["pdf_path"],
                        "run_cost_usd": f"{cost:.4f}",
                        "status": "ok",
                        "exclusion_reason": "",
                    }
                )
                done_ok += 1
                elapsed = time.time() - started
                avg = elapsed / max(done_ok, 1)
                remaining = (total - idx) * (avg / 60.0)
                print(
                    f"  FINISH {p.firm} · ${cost:.2f} · "
                    f"{pr.get('searches_recommended')}/{pr.get('searches_total')} · "
                    f"spent ${spent:.2f} · remaining ~{remaining:.0f} min",
                    flush=True,
                )
                write_progress(
                    progress_path,
                    done=done_ok,
                    total=total,
                    current="(idle)",
                    last=f"ok · {p.firm}",
                    spent=spent,
                    eta_min=remaining,
                )
                if done_ok == args.pause_after and not args.skip_pause and idx < total:
                    print(
                        f"\n*** PAUSE after {done_ok} successes — "
                        "Product Analyst sniff window. Press Enter to continue overnight batch "
                        "(or Ctrl+C to stop). ***\n",
                        flush=True,
                    )
                    try:
                        input()
                    except EOFError:
                        print("No TTY; continuing after pause-after (EOF).", flush=True)

        except Exception as exc:
            reason = str(exc)[:400]
            row["exclusion_reason"] = reason
            print(f"  FAIL {p.firm}: {reason}", flush=True)
            if is_auth_failure(reason):
                append_jsonl(jsonl_path, row)
                append_csv(csv_path, row, fields)
                write_progress(
                    progress_path,
                    done=done_ok,
                    total=total,
                    current="STOPPED",
                    last=f"auth fail · {p.firm}",
                    spent=spent,
                    eta_min=None,
                    note=f"Hard stop: {reason}",
                )
                maybe_touch_status(vault, done=done_ok, total=total, force=True)
                print("FATAL: auth/provider failure — stopping batch.", flush=True)
                return 3
            write_progress(
                progress_path,
                done=done_ok,
                total=total,
                current="(idle)",
                last=f"fail · {p.firm}",
                spent=spent,
                eta_min=(total - idx) * per_firm_min,
                note=f"Excluded: {reason[:200]}",
            )

        append_jsonl(jsonl_path, row)
        append_csv(csv_path, row, fields)
        maybe_touch_status(vault, done=done_ok, total=total, force=(row["status"] != "ok"))

    write_progress(
        progress_path,
        done=done_ok,
        total=total,
        current="(complete)",
        last="batch finished",
        spent=spent,
        eta_min=0,
        note=f"Final: {done_ok} ok of {total} attempted · ${spent:.2f}",
    )
    maybe_touch_status(vault, done=done_ok, total=total, force=True)
    print(f"Done. {done_ok}/{total} ok · ${spent:.2f} · PDFs in {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
