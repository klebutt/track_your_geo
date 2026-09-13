"""Customer-facing AI Recommend export (markdown + PDF). Vault handoff only."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tygeo.plain_report import EM_DASH, build_plain_report, customer_model_labels

# Operator locality codes — strip from customer export (not ordinary English words).
STANCE_CODE_RE = re.compile(
    r"`?(local_only|local_primary|remote_primary)`?"
    r"|\blocality_stance\b"
    r"|\bonline_remote\b"
    r"|Locality \(inferred[^\n]*\)",
    flags=re.IGNORECASE,
)


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def safe_firm_filename(firm: str) -> str:
    """Hyphen-only firm segment for [Firm]-AI-recommend.pdf (no spaces)."""
    name = (firm or "Firm").strip() or "Firm"
    name = name.replace("&", " and ")
    # Turn punctuation into separators before stripping non-alnum
    name = re.sub(r"[<>:\"/\\\\|?*'_.]+", "-", name)
    name = re.sub(r"[^A-Za-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "Firm"


def pdf_filename_for_firm(firm: str) -> str:
    return f"{safe_firm_filename(firm)}-AI-recommend.pdf"


def _plain_from_run(run: dict[str, Any]):
    """Always rebuild so export picks up latest Sales-locked copy."""
    snap = run.get("profile_snapshot") or {}
    return build_plain_report(
        status=str(run.get("status") or ""),
        brand_name=str(run.get("brand_name") or ""),
        model_name=str(run.get("model_name") or ""),
        query_results=list(run.get("query_results") or []),
        locality_stance=str(snap.get("locality_stance") or "") or None,
        location=str(snap.get("location") or run.get("location") or "") or None,
    )


def _unique_queries(run: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for row in run.get("query_results") or []:
        q = str(_row_get(row, "query_text") or "").strip()
        if not q or q in seen:
            continue
        seen.add(q)
        out.append(q)
    return out


def _services(snap: dict[str, Any]) -> list[str]:
    raw = snap.get("services") or snap.get("inferred_services") or []
    if isinstance(raw, str):
        return [s.strip() for s in raw.split("·") if s.strip()]
    if isinstance(raw, list):
        return [str(s).strip() for s in raw if str(s).strip()]
    return []


def build_customer_markdown(run: dict[str, Any]) -> str:
    """Customer body only — no internal notes, no locality stance codes."""
    pr = _plain_from_run(run)
    if not pr.ready:
        raise ValueError("plain_report not ready for export")

    brand = str(run.get("brand_name") or "Your firm").strip()
    snap = run.get("profile_snapshot") or {}
    loc = str(snap.get("location") or run.get("location") or "").strip()
    url = str(run.get("source_url") or snap.get("source_url") or "").strip()
    vis = float(run.get("visibility_rate") or 0.0)
    composite = float(run.get("composite_score") or 0.0)
    models = str(run.get("model_name") or "")

    lines: list[str] = []
    lines.append(f"# AI recommendation report - {brand}")
    lines.append("")
    lines.append("## Your AI recommendation report")
    lines.append("")
    if pr.what_this_is:
        lines.append(_no_em(pr.what_this_is))
        lines.append("")
    lines.append(f"**{pr.headline}**")
    lines.append("")
    lines.append(
        f"That is **{pr.searches_recommended} of {pr.searches_total}** "
        f"customer-intent questions where at least one AI reply named **{brand}**."
    )
    lines.append("")

    lines.append("### Who showed up instead")
    lines.append("")
    if pr.loss_entries:
        if pr.competitor_summary:
            lines.append(_no_em(pr.competitor_summary))
            lines.append("")
        for entry in pr.loss_entries:
            names = ", ".join(entry.competitors) if entry.competitors else "Other firms"
            q = _no_em(entry.query)
            lines.append(f"- **{names}** - on “{q}”")
        lines.append("")
    else:
        # Empty losses: one line only (do not also print competitor_summary above)
        lines.append(
            _no_em(
                pr.competitor_summary
                or "No tracked competitors were named on the searches where you were missing."
            )
        )
        lines.append("")

    lines.append("### What this means")
    lines.append("")
    # gap_summary only - do not repeat competitor_summary (already above)
    lines.append(_no_em(pr.gap_summary or pr.meaning or ""))
    lines.append("")
    if pr.geography_note and not STANCE_CODE_RE.search(pr.geography_note):
        lines.append(f"*{_no_em(pr.geography_note)}*")
        lines.append("")

    if pr.deeper_insights:
        lines.append("### Optional deeper next steps")
        lines.append("")
        lead = _currency_safe(pr.deeper_insights_lead or "")
        if lead:
            lines.append(_no_em(lead))
            lines.append("")
        for item in pr.deeper_insights:
            lines.append(f"#### {_no_em(item.title)}")
            lines.append("")
            lines.append(_no_em(item.detail))
            lines.append("")

    if pr.models_note:
        lines.append(f"*{_no_em(pr.models_note)}*")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Snapshot (what we measured)")
    lines.append("")
    lines.append("| | |")
    lines.append("|--|--|")
    lines.append(f"| Firm | {brand} |")
    if loc:
        lines.append(f"| Location used | {loc} |")
    if url:
        lines.append(f"| Website | {url} |")
    lines.append(f"| Visibility (probes with brand name in reply) | **{vis * 100:.0f}%** |")
    lines.append(f"| Composite index | **{composite:.1f}** / 100 |")
    labels = customer_model_labels(models)
    if labels:
        lines.append(f"| Models | {', '.join(labels)} |")
    lines.append("")
    if pr.index_note:
        lines.append(_no_em(pr.index_note))
        lines.append("")

    services = _services(snap)
    if services:
        lines.append("**Services inferred from the site:** " + ", ".join(services))
        lines.append("")

    queries = _unique_queries(run)
    if queries:
        lines.append("## Questions we asked (brand-neutral)")
        lines.append("")
        for i, q in enumerate(queries, 1):
            lines.append(f"{i}. {_no_em(q)}")
        lines.append("")

    body = "\n".join(lines).strip() + "\n"
    body = STANCE_CODE_RE.sub("", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    body = _currency_safe(body)
    if EM_DASH in body:
        body = body.replace(EM_DASH, " - ")
    return body


def _no_em(text: str) -> str:
    return (text or "").replace(EM_DASH, " - ")


def _currency_safe(text: str) -> str:
    """Normalise pound amounts to '£N-N' (real £ / U+00A3; never mojibake or GBP 5?20)."""
    s = text or ""
    s = re.sub(
        r"(?:£|\u00a3|\uFFFD|GBP\s*)\s*(\d+)\s*[\u2013\u2014\-–—?]+\s*(\d+)",
        r"£\1-\2",
        s,
        flags=re.IGNORECASE,
    )
    s = s.replace("\u2013", "-").replace("\u2014", " - ")
    return s


def build_customer_html(markdown: str, *, title: str) -> str:
    """Minimal HTML for PDF print (not a full markdown renderer)."""
    # Prefer calling build_customer_markdown then a light structure — PDF writer uses sections.
    escaped_title = (
        title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    # Keep markdown as pre-wrapped paragraphs via simple conversion
    blocks = []
    for para in markdown.split("\n\n"):
        p = para.strip()
        if not p:
            continue
        safe = (
            p.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )
        if p.startswith("# "):
            blocks.append(f"<h1>{safe[2:]}</h1>")
        elif p.startswith("## "):
            blocks.append(f"<h2>{safe[3:]}</h2>")
        elif p.startswith("### "):
            blocks.append(f"<h3>{safe[4:]}</h3>")
        elif p.startswith("#### "):
            blocks.append(f"<h4>{safe[5:]}</h4>")
        else:
            blocks.append(f"<p>{safe}</p>")
    body = "\n".join(blocks)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{escaped_title}</title>
<style>
  body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 720px; margin: 2rem auto;
         color: #1e293b; line-height: 1.45; }}
  h1,h2,h3,h4 {{ font-family: system-ui, sans-serif; color: #0f172a; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  td, th {{ border: 1px solid #cbd5e1; padding: 0.35rem 0.5rem; text-align: left; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def _to_fpdf_markdown(text: str) -> str:
    """Map CommonMark-ish *italic* to fpdf2 __italic__; keep **bold**."""
    s = text or ""
    bold_parts: list[str] = []

    def _hold_bold(m: re.Match[str]) -> str:
        bold_parts.append(m.group(0))
        return f"\x00BOLD{len(bold_parts) - 1}\x00"

    s = re.sub(r"\*\*[^*]+\*\*", _hold_bold, s)
    s = re.sub(r"(?<![*_])\*([^*]+)\*(?![*_])", r"__\1__", s)
    for i, part in enumerate(bold_parts):
        s = s.replace(f"\x00BOLD{i}\x00", part)
    return s


def write_customer_pdf(markdown: str, dest: Path, *, firm: str) -> Path:
    """Render customer markdown to a styled PDF (no raw **, *, or - markers)."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)
    pdf.set_text_color(30, 41, 59)

    def scrub(s: str) -> str:
        out = _currency_safe(s)
        out = (
            out.replace("“", '"')
            .replace("”", '"')
            .replace("’", "'")
            .replace("‘", "'")
            .replace(EM_DASH, " - ")
            .replace("\u2013", "-")
        )
        return out.encode("latin-1", "ignore").decode("latin-1")

    def write_md(text: str, *, size: int = 11, style: str = "", gap: float = 3, color=None):
        raw = scrub(_to_fpdf_markdown(text)).strip()
        if not raw:
            return
        if color is not None:
            pdf.set_text_color(*color)
        else:
            pdf.set_text_color(30, 41, 59)
        pdf.set_font("Helvetica", style=style, size=size)
        pdf.multi_cell(
            0,
            6,
            raw,
            markdown=True,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        if gap:
            pdf.ln(gap)

    write_md(f"AI Recommend - {firm}", size=16, style="B", gap=4)

    for para in markdown.split("\n\n"):
        p = para.strip()
        if not p or p.startswith("# AI recommendation"):
            continue
        if p == "---":
            pdf.ln(3)
            continue
        if p.startswith("## "):
            write_md(p[3:].strip(), size=13, style="B", gap=3)
            continue
        if p.startswith("### "):
            write_md(p[4:].strip(), size=12, style="B", gap=2)
            continue
        if p.startswith("#### "):
            write_md(p[5:].strip(), size=11, style="B", gap=2)
            continue
        if p.startswith("|"):
            for line in p.split("\n"):
                if line.startswith("|--") or not line.startswith("|"):
                    continue
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 2 and cells[0]:
                    label = re.sub(r"\*+", "", cells[0]).strip()
                    value = cells[1]
                    write_md(f"**{label}:** {value}", size=10, gap=1)
            pdf.ln(2)
            continue

        for line in p.split("\n"):
            line = line.strip()
            if not line:
                continue
            m_bullet = re.match(r"^[-*]\s+(.*)$", line)
            m_num = re.match(r"^(\d+)\.\s+(.*)$", line)
            if m_bullet:
                write_md(f"\xb7 {m_bullet.group(1)}", size=11, gap=1)
            elif m_num:
                write_md(f"{m_num.group(1)}. {m_num.group(2)}", size=11, gap=1)
            elif (
                len(line) >= 2
                and line.startswith("*")
                and line.endswith("*")
                and not line.startswith("**")
            ):
                inner = line[1:-1].strip()
                write_md(f"*{inner}*", size=10, gap=2, color=(100, 116, 139))
            else:
                write_md(line, size=11, gap=2)

    pdf.set_text_color(100, 116, 139)
    pdf.set_font("Helvetica", size=8)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.multi_cell(
        0,
        5,
        scrub(f"Generated {stamp} | AI Recommend"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    pdf.output(str(dest))
    return dest


def export_customer_report(
    run: dict[str, Any],
    out_dir: Path,
    *,
    also_markdown: bool = True,
) -> dict[str, Any]:
    """Write PDF (+ optional .md) into out_dir. Returns paths and meta."""
    brand = str(run.get("brand_name") or "Firm").strip() or "Firm"
    md = build_customer_markdown(run)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_name = pdf_filename_for_firm(brand)
    pdf_path = out_dir / pdf_name
    write_customer_pdf(md, pdf_path, firm=brand)
    md_path = None
    if also_markdown:
        md_path = out_dir / pdf_name.replace(".pdf", ".md")
        md_path.write_text(md, encoding="utf-8")
    return {
        "firm": brand,
        "pdf_path": str(pdf_path),
        "md_path": str(md_path) if md_path else None,
        "pdf_filename": pdf_name,
    }
