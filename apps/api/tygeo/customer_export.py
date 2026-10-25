"""Customer-facing AI Recommend export (markdown + PDF). Vault handoff only."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tygeo import brand as _brand
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
    pr = build_plain_report(
        status=str(run.get("status") or ""),
        brand_name=str(run.get("brand_name") or ""),
        model_name=str(run.get("model_name") or ""),
        query_results=list(run.get("query_results") or []),
        locality_stance=str(snap.get("locality_stance") or "") or None,
        location=str(snap.get("location") or run.get("location") or "") or None,
    )

    # Support for sample report banner (passed via _sample_banner field)
    sample_banner = run.get("_sample_banner")
    if sample_banner and pr.what_this_is:
        pr.what_this_is = f"{sample_banner}\n\n{pr.what_this_is}"

    return pr


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
    lines.append(f"| Mentioned in AI replies | **{vis * 100:.0f}% of replies** |")
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


def write_customer_pdf(run: dict[str, Any], dest: Path, *, firm: str) -> Path:
    """Structured customer PDF — branded header/footer, title block, hero, snapshot table."""
    from fpdf import FPDF
    from fpdf.enums import Align, XPos, YPos

    pr = _plain_from_run(run)
    if not pr.ready:
        raise ValueError("plain_report not ready for PDF export")

    brand = str(run.get("brand_name") or firm).strip() or firm
    snap = run.get("profile_snapshot") or {}
    loc = str(snap.get("location") or run.get("location") or "").strip()
    url = str(run.get("source_url") or snap.get("source_url") or "").strip()
    vis = float(run.get("visibility_rate") or 0.0)
    composite = float(run.get("composite_score") or 0.0)
    model_labels = customer_model_labels(str(run.get("model_name") or ""))
    x, n = pr.searches_recommended, pr.searches_total

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    primary = _brand.COLOR_PRIMARY
    primary_dark = _brand.COLOR_PRIMARY_DARK
    muted = _brand.COLOR_TEXT_MUTED
    border = _brand.COLOR_BORDER
    bg_alt = _brand.COLOR_BG_ALT

    def scrub(s: str) -> str:
        out = _currency_safe(s)
        out = (
            out.replace(""", '"')
            .replace(""", '"')
            .replace("'", "'")
            .replace("'", "'")
            .replace(EM_DASH, " - ")
            .replace("\u2013", "-")
        )
        return out.encode("latin-1", "ignore").decode("latin-1")

    header_firm_name = scrub(brand)

    class _BrandedPDF(FPDF):
        """A4 report with AI Recommend wordmark header and domain/page footer."""

        def header(self) -> None:  # fpdf hook, runs on every page
            top = 11.0
            # Small mark: rounded square with "AI" (mirrors site favicon)
            self.set_fill_color(*primary)
            self.rect(self.l_margin, top, 7, 7, style="F", round_corners=True, corner_radius=1.4)
            self.set_xy(self.l_margin, top)
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", style="B", size=8)
            self.cell(7, 7, "AI", align=Align.C)
            # Wordmark
            self.set_xy(self.l_margin + 9, top)
            self.set_text_color(*primary)
            self.set_font("Helvetica", style="B", size=12)
            self.cell(60, 7, "AI Recommend")
            # Right-hand firm name
            self.set_xy(self.l_margin, top)
            self.set_text_color(*muted)
            self.set_font("Helvetica", size=8)
            self.cell(0, 7, header_firm_name, align=Align.R)
            # Rule
            self.set_draw_color(*border)
            self.set_line_width(0.3)
            self.line(self.l_margin, top + 10, self.w - self.r_margin, top + 10)
            self.set_xy(self.l_margin, self.t_margin)

        def footer(self) -> None:  # fpdf hook, runs on every page
            y = self.h - 14
            self.set_draw_color(*border)
            self.set_line_width(0.3)
            self.line(self.l_margin, y, self.w - self.r_margin, y)
            self.set_xy(self.l_margin, y + 2)
            self.set_font("Helvetica", size=8)
            self.set_text_color(*primary)
            self.cell(60, 5, _brand.SITE_DOMAIN, link=f"https://{_brand.SITE_DOMAIN}")
            self.set_xy(self.l_margin, y + 2)
            self.set_text_color(*muted)
            self.cell(0, 5, f"Page {self.page_no()} of {{nb}}", align=Align.R)

    pdf = _BrandedPDF(format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.set_margins(20, 28, 20)
    pdf.add_page()
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    label_w = 52.0
    value_w = page_w - label_w
    row_h = 7.0


    def write_md(
        text: str,
        *,
        size: int = 11,
        style: str = "",
        gap: float = 3,
        color: tuple[int, int, int] | None = None,
        lh: float = 6,
    ) -> None:
        raw = scrub(_to_fpdf_markdown(text)).strip()
        if not raw:
            return
        pdf.set_text_color(*(color or (30, 41, 59)))
        pdf.set_font("Helvetica", style=style, size=size)
        pdf.multi_cell(0, lh, raw, markdown=True, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if gap:
            pdf.ln(gap)

    def section_break(extra: float = 5) -> None:
        pdf.ln(extra)

    def heading(text: str, *, size: int = 12, gap: float = 3) -> None:
        write_md(text, size=size, style="B", gap=gap, color=primary_dark)

    # Cover / title block: tinted panel with brand accent bar
    # Use run date if available, otherwise fall back to build date
    run_date_raw = run.get("created_at") or run.get("run_date") or run.get("started_at")
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
    report_date = f"{run_dt.day} {run_dt:%B %Y}"
    block_y = pdf.get_y()
    block_h = 27.0
    pdf.set_fill_color(*bg_alt)
    pdf.rect(pdf.l_margin, block_y, page_w, block_h, style="F")
    pdf.set_fill_color(*primary)
    pdf.rect(pdf.l_margin, block_y, 1.6, block_h, style="F")
    inner_x = pdf.l_margin + 7
    pdf.set_xy(inner_x, block_y + 4)
    pdf.set_text_color(*primary_dark)
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.cell(0, 7, scrub("Your AI recommendation report"), new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_x(inner_x)
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", style="B", size=18)
    pdf.cell(0, 9, scrub(brand), new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_x(inner_x)
    pdf.set_text_color(*muted)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 5, scrub(f"Report date: {report_date}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_xy(pdf.l_margin, block_y + block_h + 5)

    # Sample report callout box (tinted highlight for sample reports only)
    sample_banner = run.get("_sample_banner")
    if sample_banner:
        callout_y = pdf.get_y()
        callout_text = scrub(sample_banner)
        pdf.set_font("Helvetica", style="B", size=9)
        text_h = pdf.multi_cell(
            page_w - 14, 4.5, callout_text, dry_run=True, output="HEIGHT"
        )
        callout_h = text_h + 10  # 5pt padding top + 5pt padding bottom
        # Light blue tinted background (#dbeafe / rgb 219,234,254)
        pdf.set_fill_color(219, 234, 254)
        pdf.rect(pdf.l_margin, callout_y, page_w, callout_h, style="F")
        pdf.set_xy(pdf.l_margin + 7, callout_y + 5)
        pdf.set_text_color(*primary_dark)
        pdf.set_font("Helvetica", style="B", size=9)
        pdf.multi_cell(page_w - 14, 4.5, callout_text, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_y(callout_y + callout_h + 6)  # spacing after callout box
        # Get original what_this_is without the prepended banner
        original_what_this_is = pr.what_this_is
        if original_what_this_is and sample_banner in original_what_this_is:
            original_what_this_is = original_what_this_is.replace(
                f"{sample_banner}\n\n", "", 1
            )
        if original_what_this_is:
            write_md(original_what_this_is, size=10, gap=0, color=(71, 85, 105), lh=5.5)
    elif pr.what_this_is:
        write_md(pr.what_this_is, size=10, gap=0, color=(71, 85, 105), lh=5.5)
    section_break(6)

    # Hero X of N
    pdf.set_text_color(*primary)
    pdf.set_font("Helvetica", style="B", size=32)
    pdf.cell(0, 14, scrub(f"{x} of {n}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    write_md(
        f"customer-intent questions where at least one AI reply named **{brand}**.",
        size=11,
        gap=0,
        lh=5.5,
    )
    section_break(7)

    heading("Who showed up instead")
    if pr.loss_entries:
        if pr.competitor_summary:
            write_md(pr.competitor_summary, size=10, gap=2, color=(71, 85, 105), lh=5)
        for entry in pr.loss_entries:
            names = ", ".join(entry.competitors) if entry.competitors else "Other firms"
            write_md(
                f"**{names}** - on \"{_no_em(entry.query)}\"",
                size=10,
                gap=0.5,
                lh=4.8,
            )
    else:
        write_md(
            pr.competitor_summary
            or "No tracked competitors were named on the searches where you were missing.",
            size=10,
            gap=0,
            lh=5,
        )
    section_break(6)

    heading("What this means")
    write_md(pr.gap_summary or pr.meaning or "", size=11, gap=2)
    if pr.geography_note and not STANCE_CODE_RE.search(pr.geography_note):
        write_md(pr.geography_note, size=9, gap=0, color=(100, 116, 139), lh=5)
    section_break(5)

    if pr.deeper_insights:
        heading("Optional deeper next steps")
        if pr.deeper_insights_lead:
            write_md(pr.deeper_insights_lead, size=10, gap=3, color=(71, 85, 105), lh=5)
        for item in pr.deeper_insights:
            # Keep each title + detail together rather than splitting one line over a page
            pdf.set_font("Helvetica", size=10)
            need = 6 + pdf.multi_cell(
                0, 5, scrub(_to_fpdf_markdown(item.detail)).strip(), markdown=True,
                dry_run=True, output="HEIGHT",
            )
            if pdf.get_y() + need > pdf.page_break_trigger:
                pdf.add_page()
            write_md(item.title, size=11, style="B", gap=1)
            write_md(item.detail, size=10, gap=2, color=(71, 85, 105), lh=5)

    if pr.models_note:
        section_break(3)
        write_md(pr.models_note, size=9, gap=0, color=(100, 116, 139), lh=5)

    section_break(6)
    heading("Snapshot (what we measured)")
    if loc:
        write_md(f"Location: {loc}", size=9, gap=0.5, color=(71, 85, 105), lh=4.5)
    if url:
        write_md(url, size=9, gap=2, color=(71, 85, 105), lh=4.5)

    snapshot_rows = [
        ("Mentioned in AI replies", f"{vis * 100:.0f}% of replies"),
        ("Composite", f"{composite:.1f} / 100"),
        ("Models", ", ".join(model_labels) if model_labels else "n/a"),
    ]
    pdf.set_draw_color(*border)
    pdf.set_line_width(0.3)
    pdf.set_fill_color(*bg_alt)
    pdf.set_text_color(30, 41, 59)
    for label, value in snapshot_rows:
        pdf.set_font("Helvetica", size=9)
        pdf.cell(label_w, row_h, scrub(label), border=1, fill=True)
        pdf.set_font("Helvetica", style="B", size=9)
        pdf.cell(value_w, row_h, scrub(value), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)
    if pr.index_note:
        write_md(pr.index_note, size=9, gap=3, color=(100, 116, 139), lh=5)

    services = _services(snap)
    if services:
        section_break(3)
        write_md("Services inferred from the site: " + ", ".join(services), size=9, gap=2, lh=5)

    queries = _unique_queries(run)
    if queries:
        section_break(4)
        heading("Questions we asked (brand-neutral)", size=11, gap=2)
        for i, q in enumerate(queries, 1):
            write_md(f"{i}. {_no_em(q)}", size=9, gap=0.8, lh=4.8, color=(71, 85, 105))

    section_break(4)
    pdf.set_text_color(100, 116, 139)
    pdf.set_font("Helvetica", size=8)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.multi_cell(0, 4, scrub(f"Generated {stamp}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

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
    write_customer_pdf(run, pdf_path, firm=brand)
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
