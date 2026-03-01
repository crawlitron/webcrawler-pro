import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _safe_import_reportlab():
    try:
        return True
    except ImportError:
        return False


def generate_crawl_pdf(crawl, pages, issues, project) -> bytes:
    """
    Generate a comprehensive PDF report for a crawl.
    Args:
        crawl: Crawl ORM object
        pages: list of Page ORM objects
        issues: list of Issue ORM objects
        project: Project ORM object
    Returns bytes of the PDF.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak,
    )
    from reportlab.lib.enums import TA_CENTER

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="WebCrawler Pro Report — {}".format(project.name),
        author="WebCrawler Pro",
    )

    styles = getSampleStyleSheet()
    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=28,
        textColor=colors.HexColor("#1e40af"),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    h1_style = ParagraphStyle(
        "H1", parent=styles["Heading1"],
        fontSize=18, textColor=colors.HexColor("#1e3a5f"),
        spaceBefore=16, spaceAfter=8,
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=14, textColor=colors.HexColor("#374151"),
        spaceBefore=10, spaceAfter=6,
    )
    body_style = styles["Normal"]
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#6b7280")
    )
    center_style = ParagraphStyle(
        "Center", parent=styles["Normal"], alignment=TA_CENTER
    )

    # Colors
    COLOR_CRITICAL = colors.HexColor("#fee2e2")
    COLOR_WARNING = colors.HexColor("#fef9c3")
    COLOR_INFO = colors.HexColor("#dbeafe")
    COLOR_HEADER = colors.HexColor("#1e40af")
    COLOR_HEADER_TEXT = colors.white
    COLOR_ROW_ALT = colors.HexColor("#f9fafb")
    COLOR_BORDER = colors.HexColor("#e5e7eb")

    def hr():
        return HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=8)

    def table_style_base(header_rows=1):
        style = [
            ("BACKGROUND", (0, 0), (-1, header_rows - 1), COLOR_HEADER),
            ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), COLOR_HEADER_TEXT),
            ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, header_rows - 1), 9),
            ("FONTSIZE", (0, header_rows), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, COLOR_ROW_ALT]),
            ("GRID", (0, 0), (-1, -1), 0.3, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        return style

    story = []
    total_issues = (crawl.critical_issues or 0) + (crawl.warning_issues or 0) + (crawl.info_issues or 0)
    report_date = datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC")
    completed = crawl.completed_at.strftime("%d.%m.%Y %H:%M") if crawl.completed_at else "N/A"
    started = crawl.started_at.strftime("%d.%m.%Y %H:%M") if crawl.started_at else "N/A"

    # ─── PAGE 1: Title ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("WebCrawler Pro", title_style))
    story.append(Paragraph("SEO & Accessibility Report", ParagraphStyle(
        "Sub", parent=styles["Normal"], fontSize=16,
        textColor=colors.HexColor("#6b7280"), alignment=TA_CENTER, spaceAfter=24
    )))
    story.append(hr())
    story.append(Spacer(1, 0.5 * cm))

    cover_data = [
        ["Projektname", Paragraph("<b>{}</b>".format(project.name), body_style)],
        ["Start-URL", Paragraph(project.start_url, small_style)],
        ["Crawl-ID", str(crawl.id)],
        ["Gestartet", started],
        ["Abgeschlossen", completed],
        ["Berichtsdatum", report_date],
    ]
    cover_table = Table(cover_data, colWidths=[5 * cm, None])
    cover_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, COLOR_ROW_ALT]),
        ("GRID", (0, 0), (-1, -1), 0.3, COLOR_BORDER),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 1 * cm))

    # Quick stats
    stats_data = [
        ["URLs gecrawlt", "Kritische Issues", "Warnungen", "Infos"],
        [
            str(crawl.crawled_urls or 0),
            str(crawl.critical_issues or 0),
            str(crawl.warning_issues or 0),
            str(crawl.info_issues or 0),
        ],
    ]
    stats_table = Table(stats_data, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
    stats_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_HEADER_TEXT),
        ("BACKGROUND", (1, 1), (1, 1), COLOR_CRITICAL),
        ("BACKGROUND", (2, 1), (2, 1), COLOR_WARNING),
        ("BACKGROUND", (3, 1), (3, 1), COLOR_INFO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, COLOR_BORDER),
    ]))
    story.append(stats_table)
    story.append(PageBreak())

    # ─── PAGE 2: Executive Summary ──────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", h1_style))
    story.append(hr())

    # Calculate SEO score heuristic
    seo_score = 100
    if crawl.crawled_urls and crawl.crawled_urls > 0:
        issue_rate = total_issues / crawl.crawled_urls
        seo_score = max(0, int(100 - issue_rate * 10))
        critical_penalty = min(50, (crawl.critical_issues or 0) * 2)
        seo_score = max(0, seo_score - critical_penalty)

    # Performance score average
    perf_scores = [p.performance_score for p in pages if p.performance_score is not None]
    avg_perf = int(sum(perf_scores) / len(perf_scores)) if perf_scores else 0

    summary_data = [
        ["Metrik", "Wert", "Bewertung"],
        ["Gesamt-URLs", str(crawl.crawled_urls or 0), "—"],
        ["SEO Score (Schätzung)", "{}/100".format(seo_score),
         "Gut" if seo_score >= 80 else ("Mittel" if seo_score >= 50 else "Kritisch")],
        ["Ø Performance Score", "{}/100".format(avg_perf),
         "Gut" if avg_perf >= 80 else ("Mittel" if avg_perf >= 50 else "Schlecht")],
        ["Kritische Issues", str(crawl.critical_issues or 0),
         "OK" if (crawl.critical_issues or 0) == 0 else "Handlungsbedarf!"],
        ["Warnungen", str(crawl.warning_issues or 0), "—"],
        ["Informationen", str(crawl.info_issues or 0), "—"],
        ["Fehlgeschlagene URLs", str(crawl.failed_urls or 0), "—"],
    ]
    summary_table = Table(summary_data, colWidths=[7 * cm, 4 * cm, 5 * cm])
    summary_table.setStyle(TableStyle(table_style_base()))
    story.append(summary_table)
    story.append(Spacer(1, 0.5 * cm))

    # Response time stats
    resp_times = [p.response_time for p in pages if p.response_time is not None]
    avg_resp = (sum(resp_times) / len(resp_times) * 1000) if resp_times else 0
    slow_pages = [p for p in pages if p.response_time and p.response_time > 3.0]

    story.append(Paragraph("Key Performance Metrics", h2_style))
    perf_data = [
        ["Metric", "Wert"],
        ["Ø Response Time", "{:.0f} ms".format(avg_resp)],
        ["Seiten > 3s", str(len(slow_pages))],
        ["Nicht-indexierbare Seiten", str(sum(1 for p in pages if not p.is_indexable))],
        ["Seiten mit 4xx Fehler", str(sum(1 for p in pages if p.status_code and 400 <= p.status_code < 500))],
        ["Seiten mit 5xx Fehler", str(sum(1 for p in pages if p.status_code and p.status_code >= 500))],
        ["Bilder ohne Alt-Text", str(sum(p.images_without_alt or 0 for p in pages))],
    ]
    perf_table = Table(perf_data, colWidths=[9 * cm, 7 * cm])
    perf_table.setStyle(TableStyle(table_style_base()))
    story.append(perf_table)
    story.append(PageBreak())

    # ─── PAGE 3-4: SEO-Analyse ──────────────────────────────────────────────────
    story.append(Paragraph("SEO-Analyse", h1_style))
    story.append(hr())

    # Issue distribution
    story.append(Paragraph("Issue-Verteilung", h2_style))
    dist_data = [
        ["Schweregrad", "Anzahl", "Anteil"],
        ["Kritisch", str(crawl.critical_issues or 0),
         "{:.1f}%".format(100 * (crawl.critical_issues or 0) / max(total_issues, 1))],
        ["Warnung", str(crawl.warning_issues or 0),
         "{:.1f}%".format(100 * (crawl.warning_issues or 0) / max(total_issues, 1))],
        ["Info", str(crawl.info_issues or 0),
         "{:.1f}%".format(100 * (crawl.info_issues or 0) / max(total_issues, 1))],
        ["Gesamt", str(total_issues), "100%"],
    ]
    dist_table = Table(dist_data, colWidths=[6 * cm, 5 * cm, 5 * cm])
    sty = table_style_base()
    sty.extend([
        ("BACKGROUND", (0, 1), (-1, 1), COLOR_CRITICAL),
        ("BACKGROUND", (0, 2), (-1, 2), COLOR_WARNING),
        ("BACKGROUND", (0, 3), (-1, 3), COLOR_INFO),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
    ])
    dist_table.setStyle(TableStyle(sty))
    story.append(dist_table)
    story.append(Spacer(1, 0.5 * cm))

    # Top 10 issues by type
    from collections import Counter
    issue_type_counts = Counter(i.issue_type for i in issues)
    top_issue_types = issue_type_counts.most_common(10)

    story.append(Paragraph("Top 10 Issues nach Typ", h2_style))
    if top_issue_types:
        top_data = [["Issue-Typ", "Anzahl"]]
        for itype, cnt in top_issue_types:
            top_data.append([itype.replace("_", " ").title(), str(cnt)])
        top_table = Table(top_data, colWidths=[12 * cm, 4 * cm])
        top_table.setStyle(TableStyle(table_style_base()))
        story.append(top_table)
    else:
        story.append(Paragraph("Keine Issues gefunden.", body_style))
    story.append(Spacer(1, 0.5 * cm))

    # Top 10 URLs with most issues
    story.append(Paragraph("Top 10 URLs mit meisten Issues", h2_style))
    url_issue_counts = Counter(i.page_id for i in issues)
    top_pages_ids = [pid for pid, _ in url_issue_counts.most_common(10)]
    page_map = {p.id: p for p in pages}
    if top_pages_ids:
        top_url_data = [["URL", "Issues"]]
        for pid in top_pages_ids:
            page = page_map.get(pid)
            if page:
                url_short = page.url[:70] + "..." if len(page.url) > 70 else page.url
                top_url_data.append([Paragraph(url_short, small_style), str(url_issue_counts[pid])])
        top_url_table = Table(top_url_data, colWidths=[13 * cm, 3 * cm])
        top_url_table.setStyle(TableStyle(table_style_base()))
        story.append(top_url_table)
    story.append(PageBreak())

    # ─── PAGE 5-6: Barrierefreiheit ─────────────────────────────────────────────
    story.append(Paragraph("Barrierefreiheit (WCAG / BFSG)", h1_style))
    story.append(hr())

    a11y_issues = [i for i in issues if i.category == "accessibility"]

    def _sev(i):
        return i.severity.value if hasattr(i.severity, 'value') else str(i.severity)
    a11y_critical = sum(1 for i in a11y_issues if _sev(i) == "critical")
    a11y_warning = sum(1 for i in a11y_issues if _sev(i) == "warning")
    a11y_info = sum(1 for i in a11y_issues if _sev(i) == "info")
    a11y_total = len(a11y_issues)
    a11y_score = max(0, 100 - min(100, a11y_critical * 5 + a11y_warning * 2 + a11y_info))

    a11y_data = [
        ["Metrik", "Wert"],
        ["Accessibility Score", "{}/100".format(a11y_score)],
        ["Kritische A11y Issues", str(a11y_critical)],
        ["A11y Warnungen", str(a11y_warning)],
        ["A11y Infos", str(a11y_info)],
        ["Gesamt A11y Issues", str(a11y_total)],
    ]
    a11y_table = Table(a11y_data, colWidths=[9 * cm, 7 * cm])
    a11y_table.setStyle(TableStyle(table_style_base()))
    story.append(a11y_table)
    story.append(Spacer(1, 0.5 * cm))

    # Top accessibility issues
    a11y_type_counts = Counter(i.issue_type for i in a11y_issues)
    top_a11y = a11y_type_counts.most_common(10)
    story.append(Paragraph("Top Accessibility Issues", h2_style))
    if top_a11y:
        ta_data = [["Issue-Typ", "Anzahl"]]
        for itype, cnt in top_a11y:
            ta_data.append([itype.replace("_", " ").title(), str(cnt)])
        ta_table = Table(ta_data, colWidths=[12 * cm, 4 * cm])
        ta_table.setStyle(TableStyle(table_style_base()))
        story.append(ta_table)
    else:
        story.append(Paragraph("Keine Accessibility Issues gefunden.", body_style))
    story.append(PageBreak())

    # ─── PAGE 7: Performance ────────────────────────────────────────────────────
    story.append(Paragraph("Performance", h1_style))
    story.append(hr())

    story.append(Paragraph("Performance-Übersicht", h2_style))
    good_pages = [p for p in pages if p.performance_score and p.performance_score >= 80]
    ok_pages = [p for p in pages if p.performance_score and 50 <= p.performance_score < 80]
    poor_pages = [p for p in pages if p.performance_score and p.performance_score < 50]

    perf_overview = [
        ["Kategorie", "Anzahl", "Anteil"],
        ["Gut (≥80)", str(len(good_pages)),
         "{:.1f}%".format(100 * len(good_pages) / max(len(perf_scores), 1))],
        ["OK (50-79)", str(len(ok_pages)),
         "{:.1f}%".format(100 * len(ok_pages) / max(len(perf_scores), 1))],
        ["Schlecht (<50)", str(len(poor_pages)),
         "{:.1f}%".format(100 * len(poor_pages) / max(len(perf_scores), 1))],
    ]
    po_table = Table(perf_overview, colWidths=[6 * cm, 4 * cm, 6 * cm])
    po_table.setStyle(TableStyle(table_style_base()))
    story.append(po_table)
    story.append(Spacer(1, 0.5 * cm))

    # Slowest pages top 10
    story.append(Paragraph("Langsamste Seiten (Top 10)", h2_style))
    sorted_slow = sorted([p for p in pages if p.response_time], key=lambda p: p.response_time or 0, reverse=True)[:10]
    if sorted_slow:
        slow_data = [["URL", "Response Time", "Perf Score"]]
        for p in sorted_slow:
            url_short = p.url[:60] + "..." if len(p.url) > 60 else p.url
            rt_ms = "{:.0f} ms".format((p.response_time or 0) * 1000)
            perf = str(p.performance_score) if p.performance_score is not None else "—"
            slow_data.append([Paragraph(url_short, small_style), rt_ms, perf])
        slow_table = Table(slow_data, colWidths=[10 * cm, 3 * cm, 3 * cm])
        slow_table.setStyle(TableStyle(table_style_base()))
        story.append(slow_table)
    story.append(PageBreak())

    # ─── PAGE 8: Empfehlungen ───────────────────────────────────────────────────
    story.append(Paragraph("Empfehlungen", h1_style))
    story.append(hr())
    story.append(Paragraph(
        "Priorisierte Maßnahmen basierend auf den gefundenen Issues:",
        body_style
    ))
    story.append(Spacer(1, 0.3 * cm))

    # Get unique recommendations from critical issues first
    seen_recs = set()
    recs = []
    for severity_filter in ["critical", "warning", "info"]:
        for issue in issues:
            sev = issue.severity.value if hasattr(issue.severity, "value") else issue.severity
            if sev != severity_filter:
                continue
            rec = (issue.recommendation or issue.description or "").strip()
            if rec and rec not in seen_recs:
                seen_recs.add(rec)
                recs.append((severity_filter, rec))
            if len(recs) >= 20:
                break
        if len(recs) >= 20:
            break

    if recs:
        rec_data = [["Priorität", "Empfehlung"]]
        for sev, rec in recs:
            label = {"critical": "🔴 Kritisch", "warning": "🟡 Warnung", "info": "🔵 Info"}.get(sev, sev)
            rec_short = rec[:150] + "..." if len(rec) > 150 else rec
            rec_data.append([label, Paragraph(rec_short, small_style)])
        rec_table = Table(rec_data, colWidths=[4 * cm, 12 * cm])
        rec_table.setStyle(TableStyle(table_style_base()))
        story.append(rec_table)
    else:
        story.append(Paragraph("Keine Issues gefunden — ausgezeichnet!", body_style))
    story.append(PageBreak())

    # ─── PAGE 9+: URL Details (max 100) ────────────────────────────────────────
    story.append(Paragraph("URL-Details (Top 100)", h1_style))
    story.append(hr())

    pages_sample = sorted(pages, key=lambda p: len([i for i in issues if i.page_id == p.id]), reverse=True)[:100]
    if pages_sample:
        url_data = [["URL", "Status", "Titel", "Issues", "Perf"]]
        for p in pages_sample:
            url_short = p.url[:50] + "..." if len(p.url) > 50 else p.url
            title_short = (p.title or "")[:40] + "..." if len(p.title or "") > 40 else (p.title or "")
            n_issues = sum(1 for i in issues if i.page_id == p.id)
            perf = str(p.performance_score) if p.performance_score is not None else "—"
            url_data.append([
                Paragraph(url_short, small_style),
                str(p.status_code or ""),
                Paragraph(title_short, small_style),
                str(n_issues),
                perf,
            ])
        url_table = Table(url_data, colWidths=[7 * cm, 1.5 * cm, 5.5 * cm, 1.5 * cm, 1.5 * cm])
        url_table.setStyle(TableStyle(table_style_base()))
        story.append(url_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def generate_html_report(crawl, pages, issues, project) -> str:
    """Generate a simple HTML report for preview."""
    (crawl.critical_issues or 0) + (crawl.warning_issues or 0) + (crawl.info_issues or 0)
    resp_times = [p.response_time for p in pages if p.response_time is not None]
    avg_resp = (sum(resp_times) / len(resp_times) * 1000) if resp_times else 0
    perf_scores = [p.performance_score for p in pages if p.performance_score is not None]
    avg_perf = (sum(perf_scores) / len(perf_scores)) if perf_scores else 0
    completed = crawl.completed_at.strftime("%d.%m.%Y %H:%M") if crawl.completed_at else "N/A"

    from collections import Counter
    top_issues = Counter(i.issue_type for i in issues).most_common(10)

    rows = ""
    for itype, cnt in top_issues:
        rows += "<tr><td>{}</td><td>{}</td></tr>\n".format(
            itype.replace("_", " ").title(), cnt
        )

    html = """<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8">
<title>Report: {project_name}</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 24px; color: #1f2937; }}
  h1 {{ color: #1e40af; }} h2 {{ color: #374151; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  th {{ background: #1e40af; color: white; padding: 8px 12px; text-align: left; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #e5e7eb; }}
  tr:nth-child(even) {{ background: #f9fafb; }}
  .badge-critical {{ background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; }}
  .badge-warning {{ background: #fef9c3; color: #854d0e; padding: 2px 8px; border-radius: 4px; }}
  .badge-info {{ background: #dbeafe; color: #1d4ed8; padding: 2px 8px; border-radius: 4px; }}
  .stat {{ display: inline-block; padding: 16px 24px; margin: 8px; border-radius: 8px; min-width: 120px; text-align: center; }}
  .stat-label {{ font-size: 13px; color: #6b7280; }} .stat-value {{ font-size: 28px; font-weight: bold; }}
</style></head>
<body>
<h1>WebCrawler Pro — SEO Report</h1>
<p><b>Projekt:</b> {project_name} | <b>URL:</b> {start_url} | <b>Abgeschlossen:</b> {completed}</p>
<hr>
<h2>Übersicht</h2>
<div>
  <div class="stat" style="background:#dbeafe">
    <div class="stat-value">{crawled}</div><div class="stat-label">URLs gecrawlt</div>
  </div>
  <div class="stat" style="background:#fee2e2">
    <div class="stat-value">{critical}</div><div class="stat-label">Kritisch</div>
  </div>
  <div class="stat" style="background:#fef9c3">
    <div class="stat-value">{warning}</div><div class="stat-label">Warnungen</div>
  </div>
  <div class="stat" style="background:#f0fdf4">
    <div class="stat-value">{avg_resp:.0f}ms</div><div class="stat-label">Ø Response</div>
  </div>
  <div class="stat" style="background:#f0fdf4">
    <div class="stat-value">{avg_perf:.0f}</div><div class="stat-label">Ø Perf Score</div>
  </div>
</div>
<h2>Top Issues</h2>
<table><tr><th>Issue-Typ</th><th>Anzahl</th></tr>{rows}</table>
<p style="color:#6b7280; font-size:12px;">Generiert von WebCrawler Pro — {date}</p>
</body></html>""".format(
        project_name=project.name,
        start_url=project.start_url,
        completed=completed,
        crawled=crawl.crawled_urls or 0,
        critical=crawl.critical_issues or 0,
        warning=crawl.warning_issues or 0,
        avg_resp=avg_resp,
        avg_perf=avg_perf,
        rows=rows,
        date=datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC"),
    )
    return html
