"""Customer report HTML for /r/<slug>/ pages — mirrors PDF structure and copy."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import escape as html_escape
from typing import Any

from tygeo import brand as _brand
from tygeo.customer_export import (
    STANCE_CODE_RE,
    _plain_from_run,
    _services,
    _unique_queries,
    customer_model_labels,
    export_brand_name,
    format_query_display,
    prose_brand,
)
from tygeo.plain_report import EM_DASH

_BOOK_PATH = f"{_brand.SITE_DOMAIN}/book"
_BOOK_HREF = _brand.BOOKING_LINK
_EMAIL = _brand.CONTACT_EMAIL


def web_run_snapshot(run: dict[str, Any]) -> dict[str, Any]:
    """JSON-serialisable run subset for site rebuild without re-probing."""
    snap = dict(run.get("profile_snapshot") or {})
    return {
        "status": run.get("status"),
        "brand_name": run.get("brand_name"),
        "model_name": run.get("model_name"),
        "source_url": run.get("source_url"),
        "location": run.get("location"),
        "visibility_rate": run.get("visibility_rate"),
        "composite_score": run.get("composite_score"),
        "profile_snapshot": snap,
        "query_results": list(run.get("query_results") or []),
        "_sample_banner": run.get("_sample_banner"),
        "_report_export_date": run.get("_report_export_date"),
        "created_at": run.get("created_at"),
    }


def load_web_run(md_path: Any, md_text: str) -> dict[str, Any]:
    """Load run dict from .run.json sidecar or reconstruct from customer markdown."""
    from pathlib import Path

    path = Path(md_path)
    json_path = path.with_name(f"{path.stem}.run.json")
    if json_path.is_file():
        return json.loads(json_path.read_text(encoding="utf-8"))
    return run_from_customer_markdown(md_text)


def run_from_customer_markdown(md_text: str) -> dict[str, Any]:
    """Best-effort run dict from exported customer .md (vault handoff without JSON)."""
    firm_m = re.search(r"^# AI recommendation report - (.+)$", md_text, re.M)
    firm = (firm_m.group(1) if firm_m else "Fictional Firm Ltd").strip()

    counts_m = re.search(
        r"That is \*\*(\d+) of (\d+)\*\*",
        md_text,
    )
    x = int(counts_m.group(1)) if counts_m else 0
    n = int(counts_m.group(2)) if counts_m else 0

    vis_m = re.search(
        r"\| Mentioned in AI replies \| \*\*(\d+)% of replies\*\* \|",
        md_text,
    )
    vis = float(vis_m.group(1)) / 100.0 if vis_m else 0.0

    comp_m = re.search(r"\| Composite index \| \*\*([\d.]+)\*\* / 100 \|", md_text)
    composite = float(comp_m.group(1)) if comp_m else 0.0

    loc_m = re.search(r"\| Location used \| (.+?) \|", md_text)
    loc = loc_m.group(1).strip() if loc_m else ""

    url_m = re.search(r"\| Website \| (.+?) \|", md_text)
    url = url_m.group(1).strip() if url_m else ""

    models_m = re.search(r"\| Models \| (.+?) \|", md_text)
    model_labels = models_m.group(1).strip() if models_m else ""
    model_name = _labels_to_model_name(model_labels)

    queries: list[str] = []
    for qm in re.finditer(r"^\d+\.\s+(.+)$", md_text, re.M):
        queries.append(qm.group(1).strip())

    loss_entries: list[tuple[str, list[str]]] = []
    for lm in re.finditer(
        r"^- \*\*(.+?)\*\* - on [\"“](.+?)[\"”]\s*$",
        md_text,
        re.M,
    ):
        names = [s.strip() for s in lm.group(1).split(",") if s.strip()]
        loss_entries.append((lm.group(2).strip(), names))

    loss_queries = {q for q, _ in loss_entries}
    query_results: list[dict[str, Any]] = []
    wins_assigned = 0
    for q in queries:
        if q in loss_queries:
            comps = dict.fromkeys(
                next(names for qq, names in loss_entries if qq == q),
                True,
            )
            query_results.append(
                {
                    "query_text": q,
                    "brand_mentioned": False,
                    "competitors_mentioned": comps,
                }
            )
        elif wins_assigned < x:
            query_results.append(
                {"query_text": q, "brand_mentioned": True, "competitors_mentioned": {}}
            )
            wins_assigned += 1
        else:
            query_results.append(
                {"query_text": q, "brand_mentioned": False, "competitors_mentioned": {}}
            )

    if not query_results and n > 0:
        for _ in range(max(x, 0)):
            query_results.append(
                {
                    "query_text": f"Fictional query {len(query_results) + 1}",
                    "brand_mentioned": True,
                    "competitors_mentioned": {},
                }
            )
        while len(query_results) < n:
            query_results.append(
                {
                    "query_text": f"Fictional query {len(query_results) + 1}",
                    "brand_mentioned": False,
                    "competitors_mentioned": {},
                }
            )

    sample_banner = None
    sample_m = re.search(r"^> \*\*SAMPLE REPORT\*\*[^\n]*", md_text, re.M)
    if sample_m:
        sample_banner = sample_m.group(0).lstrip("> ").strip()

    services_m = re.search(
        r"\*\*Services inferred from the site:\*\* (.+)$",
        md_text,
        re.M,
    )
    services = (
        [s.strip() for s in services_m.group(1).split(",") if s.strip()]
        if services_m
        else []
    )

    return {
        "status": "completed",
        "brand_name": firm,
        "model_name": model_name,
        "source_url": url,
        "location": loc,
        "visibility_rate": vis,
        "composite_score": composite,
        "profile_snapshot": {
            "display_name": firm,
            "location": loc,
            "source_url": url,
            "services": services,
        },
        "query_results": query_results,
        "_sample_banner": sample_banner,
    }


def _labels_to_model_name(labels: str) -> str:
    """Map display labels back to raw model_name string (approximate)."""
    if not labels or labels == "n/a":
        return "gpt-5-search-api,perplexity/sonar-pro,gemini/gemini-2.5-flash"
    rev = {
        "ChatGPT search": "gpt-5-search-api",
        "Perplexity": "perplexity/sonar-pro",
        "Gemini": "gemini/gemini-2.5-flash",
    }
    parts = []
    for part in labels.split(","):
        label = part.strip()
        parts.append(rev.get(label, label))
    return ",".join(parts) if parts else ""


def _report_date_label(run: dict[str, Any]) -> str:
    run_date_raw = (
        run.get("_report_export_date")
        or run.get("created_at")
        or run.get("run_date")
        or run.get("started_at")
    )
    if run_date_raw:
        if isinstance(run_date_raw, str):
            try:
                run_dt = datetime.fromisoformat(run_date_raw.replace("Z", "+00:00"))
            except ValueError:
                run_dt = datetime.now(timezone.utc)
        elif isinstance(run_date_raw, datetime):
            run_dt = run_date_raw
        else:
            run_dt = datetime.now(timezone.utc)
    else:
        run_dt = datetime.now(timezone.utc)
    return f"{run_dt.day} {run_dt:%B %Y}"


def linkify_customer_copy(text: str) -> str:
    """Escape HTML and turn booking path + contact email into links."""
    if not text:
        return ""
    safe = html_escape(text, quote=True)
    safe = re.sub(
        rf"\b{re.escape(_BOOK_PATH)}\b",
        f'<a href="{html_escape(_BOOK_HREF, quote=True)}">{html_escape(_BOOK_PATH, quote=True)}</a>',
        safe,
    )
    safe = re.sub(
        rf"\b{re.escape(_EMAIL)}\b",
        f'<a href="mailto:{html_escape(_EMAIL, quote=True)}">{html_escape(_EMAIL, quote=True)}</a>',
        safe,
    )
    return safe


def _inline_markdown_to_html(text: str) -> str:
    """Bold/italic on text that may include linkified HTML segments."""
    if not text:
        return ""
    out: list[str] = []
    i = 0
    while i < len(text):
        if text.startswith("<a ", i):
            end = text.find("</a>", i)
            if end != -1:
                out.append(text[i : end + 4])
                i = end + 4
                continue
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                inner = _inline_markdown_to_html(text[i + 2 : end])
                out.append(f"<strong>{inner}</strong>")
                i = end + 2
                continue
        if text[i] == "*" and (i == 0 or text[i - 1] != "*"):
            end = i + 1
            while end < len(text):
                if text[end] == "*" and (end + 1 >= len(text) or text[end + 1] != "*"):
                    inner = linkify_customer_copy(text[i + 1 : end])
                    out.append(f"<em>{inner}</em>")
                    i = end + 1
                    break
                end += 1
            else:
                out.append(html_escape(text[i], quote=True))
                i += 1
                continue
        chunk_end = i + 1
        while chunk_end < len(text):
            if text[chunk_end : chunk_end + 2] == "**":
                break
            if text[chunk_end] == "*" and (chunk_end == 0 or text[chunk_end - 1] != "*"):
                break
            if text.startswith("<a ", chunk_end):
                break
            chunk_end += 1
        out.append(linkify_customer_copy(text[i:chunk_end]))
        i = chunk_end
    return "".join(out)


def _paragraph_html(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    return f"<p>{_inline_markdown_to_html(raw)}</p>"


def build_customer_report_body_html(run: dict[str, Any]) -> str:
    """Structured report body HTML aligned with write_customer_pdf layout."""
    pr = _plain_from_run(run)
    if not pr.ready:
        raise ValueError("plain_report not ready for web export")

    display_label = export_brand_name(run)
    prose = prose_brand(display_label)
    snap = run.get("profile_snapshot") or {}
    loc = str(snap.get("location") or run.get("location") or "").strip()
    url = str(run.get("source_url") or snap.get("source_url") or "").strip()
    vis = float(run.get("visibility_rate") or 0.0)
    composite = float(run.get("composite_score") or 0.0)
    model_labels = customer_model_labels(str(run.get("model_name") or ""))
    x, n = pr.searches_recommended, pr.searches_total
    report_date = _report_date_label(run)

    parts: list[str] = []
    parts.append('<article class="report-doc">')

    parts.append('<header class="report-title-block">')
    parts.append('<div class="report-title-accent" aria-hidden="true"></div>')
    parts.append('<div class="report-title-inner">')
    parts.append('<p class="report-kicker">Your AI recommendation report</p>')
    parts.append(
        f'<h1 class="report-firm-title">{html_escape(display_label, quote=True)}</h1>'
    )
    parts.append(
        f'<p class="report-meta-date">Report date: {html_escape(report_date, quote=True)}</p>'
    )
    parts.append("</div></header>")

    sample_banner = run.get("_sample_banner")
    if sample_banner:
        parts.append(
            f'<div class="report-sample-callout" role="note">'
            f"{_inline_markdown_to_html(str(sample_banner))}"
            f"</div>"
        )
        what = pr.what_this_is or ""
        if sample_banner and what.startswith(str(sample_banner)):
            what = what.replace(f"{sample_banner}\n\n", "", 1)
        if what:
            parts.append(f'<p class="report-lead">{linkify_customer_copy(what)}</p>')
    elif pr.what_this_is:
        parts.append(f'<p class="report-lead">{linkify_customer_copy(pr.what_this_is)}</p>')

    parts.append(
        f'<section class="report-hero-score" data-score="{x}-of-{n}" '
        f'aria-label="{html_escape(f"{x} of {n} customer-intent searches", quote=True)}">'
    )
    parts.append(
        f'<p class="report-hero-number">{html_escape(f"{x} of {n}", quote=True)}</p>'
    )
    parts.append(
        '<p class="report-hero-caption">'
        f"customer-intent questions where at least one AI reply named "
        f"<strong>{html_escape(prose, quote=True)}</strong>."
        "</p>"
    )
    parts.append("</section>")

    parts.append('<section class="report-section">')
    parts.append("<h2>Who showed up instead</h2>")
    if pr.loss_entries:
        if pr.competitor_summary:
            parts.append(
                f'<p class="report-muted">{linkify_customer_copy(pr.competitor_summary)}</p>'
            )
        parts.append('<ul class="report-loss-list">')
        for entry in pr.loss_entries:
            names = ", ".join(entry.competitors) if entry.competitors else "Other firms"
            q = format_query_display(entry.query)
            parts.append(
                "<li>"
                f"<strong>{html_escape(names, quote=True)}</strong> "
                f"- on &ldquo;{html_escape(q, quote=True)}&rdquo;"
                "</li>"
            )
        parts.append("</ul>")
    else:
        summary = (
            pr.competitor_summary
            or "No tracked competitors were named on the searches where you were missing."
        )
        parts.append(f'<p class="report-muted">{linkify_customer_copy(summary)}</p>')
    parts.append("</section>")

    parts.append('<section class="report-section">')
    parts.append("<h2>What this means</h2>")
    parts.append(
        f'<p>{linkify_customer_copy(pr.gap_summary or pr.meaning or "")}</p>'
    )
    if pr.geography_note and not STANCE_CODE_RE.search(pr.geography_note):
        parts.append(
            f'<p class="report-note"><em>{linkify_customer_copy(pr.geography_note)}</em></p>'
        )
    parts.append("</section>")

    if pr.deeper_insights:
        parts.append('<section class="report-section">')
        parts.append("<h2>Optional deeper next steps</h2>")
        if pr.deeper_insights_lead:
            parts.append(
                f'<p class="report-muted">{linkify_customer_copy(pr.deeper_insights_lead)}</p>'
            )
        for item in pr.deeper_insights:
            parts.append(
                f"<h3>{html_escape(item.title, quote=True)}</h3>"
            )
            parts.append(
                f'<p class="report-muted">{linkify_customer_copy(item.detail)}</p>'
            )
        parts.append("</section>")

    if pr.models_note:
        parts.append(
            f'<p class="report-note"><em>{linkify_customer_copy(pr.models_note)}</em></p>'
        )

    parts.append('<section class="report-section report-snapshot">')
    parts.append("<h2>Snapshot (what we measured)</h2>")
    if loc:
        parts.append(
            f'<p class="report-snapshot-meta">Location: {html_escape(loc, quote=True)}</p>'
        )
    if url:
        safe_url = html_escape(url, quote=True)
        parts.append(
            f'<p class="report-snapshot-meta">Website: '
            f'<a href="{safe_url}" rel="noopener noreferrer">{safe_url}</a></p>'
        )
    parts.append('<table class="report-snapshot-table">')
    parts.append("<tbody>")
    rows = [
        ("Mentioned in AI replies", f"{vis * 100:.0f}% of replies"),
        ("Composite", f"{composite:.1f} / 100"),
        ("Models", ", ".join(model_labels) if model_labels else "n/a"),
    ]
    for label, value in rows:
        parts.append("<tr>")
        parts.append(f"<th scope=\"row\">{html_escape(label, quote=True)}</th>")
        parts.append(f"<td>{html_escape(value, quote=True)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    if pr.index_note:
        parts.append(
            f'<p class="report-note">{linkify_customer_copy(pr.index_note)}</p>'
        )
    services = _services(snap)
    if services:
        parts.append(
            "<p class=\"report-services\"><strong>Services inferred from the site:</strong> "
            f"{html_escape(', '.join(services), quote=True)}</p>"
        )
    parts.append("</section>")

    queries = _unique_queries(run)
    if queries:
        parts.append('<section class="report-section">')
        parts.append("<h2>Questions we asked (brand-neutral)</h2>")
        parts.append('<ol class="report-questions">')
        for q in queries:
            parts.append(
                f"<li>{html_escape(format_query_display(q), quote=True)}</li>"
            )
        parts.append("</ol></section>")

    parts.append("</article>")
    html = "\n".join(parts)
    html = html.replace(EM_DASH, " - ")
    return html
