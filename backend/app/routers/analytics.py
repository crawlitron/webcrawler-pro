from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import Crawl, Page, Issue

router = APIRouter(prefix="/api", tags=["analytics"])


def _get_crawl_or_404(crawl_id: int, db: Session) -> Crawl:
    crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()
    if not crawl:
        raise HTTPException(404, "Crawl not found")
    return crawl


@router.get("/crawls/{crawl_id}/analytics/overview")
def analytics_overview(crawl_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Summary of all crawl metrics."""
    crawl = _get_crawl_or_404(crawl_id, db)
    pages_q = db.query(Page).filter(Page.crawl_id == crawl_id)
    total_pages = pages_q.count()
    avg_response = db.query(func.avg(Page.response_time)).filter(
        Page.crawl_id == crawl_id, Page.response_time.isnot(None)
    ).scalar() or 0.0
    avg_word_count = db.query(func.avg(Page.word_count)).filter(
        Page.crawl_id == crawl_id, Page.word_count > 0
    ).scalar() or 0.0
    indexable_count = pages_q.filter(Page.is_indexable == True).count()  # noqa: E712
    noindex_count = pages_q.filter(Page.is_indexable == False).count()   # noqa: E712
    pages_200 = pages_q.filter(Page.status_code == 200).count()
    pages_3xx = pages_q.filter(Page.status_code >= 300, Page.status_code < 400).count()
    pages_4xx = pages_q.filter(Page.status_code >= 400, Page.status_code < 500).count()
    pages_5xx = pages_q.filter(Page.status_code >= 500).count()
    slow_pages = pages_q.filter(Page.response_time > 3.0).count()
    images_no_alt = db.query(func.sum(Page.images_without_alt)).filter(
        Page.crawl_id == crawl_id
    ).scalar() or 0
    total_internal = db.query(func.sum(Page.internal_links_count)).filter(
        Page.crawl_id == crawl_id
    ).scalar() or 0
    total_external = db.query(func.sum(Page.external_links_count)).filter(
        Page.crawl_id == crawl_id
    ).scalar() or 0
    return {
        "crawl_id": crawl_id,
        "status": crawl.status,
        "total_urls": crawl.total_urls,
        "crawled_urls": crawl.crawled_urls,
        "failed_urls": crawl.failed_urls,
        "total_pages": total_pages,
        "critical_issues": crawl.critical_issues,
        "warning_issues": crawl.warning_issues,
        "info_issues": crawl.info_issues,
        "total_issues": crawl.critical_issues + crawl.warning_issues + crawl.info_issues,
        "avg_response_time_ms": round(avg_response * 1000, 1),
        "avg_word_count": round(float(avg_word_count), 0),
        "indexable_pages": indexable_count,
        "noindex_pages": noindex_count,
        "slow_pages": slow_pages,
        "images_missing_alt": int(images_no_alt),
        "total_internal_links": int(total_internal),
        "total_external_links": int(total_external),
        "status_distribution": {
            "2xx": pages_200,
            "3xx": pages_3xx,
            "4xx": pages_4xx,
            "5xx": pages_5xx,
        },
        "started_at": crawl.started_at.isoformat() if crawl.started_at else None,
        "completed_at": crawl.completed_at.isoformat() if crawl.completed_at else None,
    }


@router.get("/crawls/{crawl_id}/analytics/issues-by-type")
def issues_by_type(crawl_id: int, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Issues grouped by type with counts per severity."""
    _get_crawl_or_404(crawl_id, db)
    rows = db.query(
        Issue.issue_type,
        Issue.severity,
        func.count(Issue.id).label("count")
    ).filter(
        Issue.crawl_id == crawl_id
    ).group_by(
        Issue.issue_type, Issue.severity
    ).order_by(func.count(Issue.id).desc()).all()
    result: Dict[str, Dict] = {}
    for row in rows:
        key = row.issue_type
        if key not in result:
            result[key] = {"issue_type": key, "total": 0, "critical": 0, "warning": 0, "info": 0}
        result[key]["total"] += row.count
        result[key][row.severity.value] += row.count
    return sorted(result.values(), key=lambda x: x["total"], reverse=True)


@router.get("/crawls/{crawl_id}/analytics/status-distribution")
def status_distribution(crawl_id: int, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Distribution of HTTP status codes."""
    _get_crawl_or_404(crawl_id, db)
    rows = db.query(
        Page.status_code,
        func.count(Page.id).label("count")
    ).filter(Page.crawl_id == crawl_id).group_by(Page.status_code).order_by(Page.status_code).all()
    total = sum(r.count for r in rows)
    return [
        {
            "status_code": r.status_code,
            "count": r.count,
            "percent": round(r.count / total * 100, 1) if total > 0 else 0,
            "label": _status_label(r.status_code),
        }
        for r in rows
    ]


@router.get("/crawls/{crawl_id}/analytics/response-times")
def response_times_endpoint(crawl_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Response time distribution with histogram buckets."""
    _get_crawl_or_404(crawl_id, db)
    times = db.query(Page.response_time).filter(
        Page.crawl_id == crawl_id,
        Page.response_time.isnot(None),
        Page.status_code == 200
    ).all()
    values = sorted([float(r[0]) for r in times if r[0] is not None])
    if not values:
        return {"buckets": [], "avg": 0, "min": 0, "max": 0, "p50": 0, "p90": 0, "p95": 0}
    buckets = [
        {"range": "< 0.5s", "min": 0.0, "max": 0.5, "count": 0},
        {"range": "0.5-1s", "min": 0.5, "max": 1.0, "count": 0},
        {"range": "1-2s", "min": 1.0, "max": 2.0, "count": 0},
        {"range": "2-3s", "min": 2.0, "max": 3.0, "count": 0},
        {"range": "3-5s", "min": 3.0, "max": 5.0, "count": 0},
        {"range": "> 5s", "min": 5.0, "max": 9999, "count": 0},
    ]
    for v in values:
        for b in buckets:
            if b["min"] <= v < b["max"]:
                b["count"] += 1
                break
    n = len(values)
    return {
        "buckets": [{"range": b["range"], "count": b["count"]} for b in buckets],
        "avg": round(sum(values) / n, 3),
        "min": round(values[0], 3),
        "max": round(values[-1], 3),
        "p50": round(values[int(n * 0.50)], 3),
        "p90": round(values[int(n * 0.90)], 3),
        "p95": round(values[min(int(n * 0.95), n - 1)], 3),
        "total_measured": n,
    }


@router.get("/crawls/{crawl_id}/analytics/top-issues")
def top_issues(crawl_id: int, limit: int = 10,
               db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Top N most frequent issue types."""
    _get_crawl_or_404(crawl_id, db)
    rows = db.query(
        Issue.issue_type,
        Issue.severity,
        func.count(Issue.id).label("count")
    ).filter(Issue.crawl_id == crawl_id).group_by(
        Issue.issue_type, Issue.severity
    ).order_by(func.count(Issue.id).desc()).limit(limit).all()
    return [
        {
            "issue_type": r.issue_type,
            "severity": r.severity.value,
            "count": r.count,
            "label": r.issue_type.replace("_", " ").title(),
        }
        for r in rows
    ]


@router.get("/crawls/{crawl_id}/sitemap")
def generate_sitemap(crawl_id: int, db: Session = Depends(get_db)):
    """Generate sitemap.xml from crawled URLs (200 OK, indexable HTML pages)."""
    _get_crawl_or_404(crawl_id, db)
    pages = db.query(Page).filter(
        Page.crawl_id == crawl_id,
        Page.status_code == 200,
        Page.is_indexable == True,  # noqa: E712
        Page.content_type.like("%text/html%")
    ).order_by(Page.depth, Page.url).all()
    xml_lines = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>"]
    xml_lines.append("<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">")
    for page in pages:
        crawled = page.crawled_at.strftime("%Y-%m-%d") if page.crawled_at else ""
        priority_map = {0: "1.0", 1: "0.8", 2: "0.6"}
        priority = priority_map.get(page.depth, "0.4")
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{_escape_xml(page.url)}</loc>")
        if crawled:
            xml_lines.append(f"    <lastmod>{crawled}</lastmod>")
        xml_lines.append("    <changefreq>weekly</changefreq>")
        xml_lines.append(f"    <priority>{priority}</priority>")
        xml_lines.append("  </url>")
    xml_lines.append("</urlset>")
    content = "\n".join(xml_lines)
    return Response(
        content=content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=sitemap_{crawl_id}.xml"},
    )


def _status_label(code) -> str:
    if code is None:
        return "Unknown"
    if code < 300:
        return "OK"
    if code < 400:
        return "Redirect"
    if code < 500:
        return "Client Error"
    return "Server Error"


def _escape_xml(s: str) -> str:
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    return s


@router.get("/crawls/{crawl_id}/analytics/top-pages")
def top_pages_by_issues(
    crawl_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Top N pages by total issue count."""
    _get_crawl_or_404(crawl_id, db)
    rows = db.query(
        Issue.page_id,
        func.count(Issue.id).label("issue_count"),
        func.sum(
            func.cast(Issue.severity == "critical", db.bind.dialect.name == "postgresql" and func.cast(1, func.Integer) or 1)
        ).label("c"),
    ).filter(
        Issue.crawl_id == crawl_id
    ).group_by(Issue.page_id).order_by(
        func.count(Issue.id).desc()
    ).limit(limit).all()

    results = []
    for row in rows:
        page = db.query(Page).filter(Page.id == row.page_id).first()
        if not page:
            continue
        # Per-severity counts
        sev_counts = db.query(
            Issue.severity,
            func.count(Issue.id).label("cnt")
        ).filter(
            Issue.crawl_id == crawl_id,
            Issue.page_id == row.page_id,
        ).group_by(Issue.severity).all()
        critical = warning = info = 0
        for sc in sev_counts:
            if sc.severity.value == "critical":
                critical = sc.cnt
            elif sc.severity.value == "warning":
                warning = sc.cnt
            else:
                info = sc.cnt
        results.append({
            "page_id": page.id,
            "url": page.url,
            "status_code": page.status_code,
            "title": page.title,
            "issue_count": row.issue_count,
            "critical": critical,
            "warning": warning,
            "info": info,
            "depth": page.depth,
        })
    return results


@router.get("/projects/{project_id}/analytics/issue-trend")
def issue_trend(
    project_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Issue trend across the last N completed crawls for a project."""
    from ..models import Project
    if not db.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    crawls = db.query(Crawl).filter(
        Crawl.project_id == project_id,
        Crawl.status == "completed",
    ).order_by(Crawl.completed_at.asc()).limit(limit).all()
    return [
        {
            "crawl_id": c.id,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
            "total_pages": c.crawled_urls,
            "critical_issues": c.critical_issues,
            "warning_issues": c.warning_issues,
            "info_issues": c.info_issues,
            "total_issues": c.critical_issues + c.warning_issues + c.info_issues,
        }
        for c in crawls
    ]


@router.get("/crawls/{crawl_id}/analytics/issues-summary")
def issues_summary(crawl_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Percentage of pages with at least one issue."""
    crawl = _get_crawl_or_404(crawl_id, db)
    total_pages = db.query(Page).filter(Page.crawl_id == crawl_id).count()
    pages_with_issues = db.query(
        func.count(func.distinct(Issue.page_id))
    ).filter(Issue.crawl_id == crawl_id).scalar() or 0
    pct = round(pages_with_issues / total_pages * 100, 1) if total_pages > 0 else 0.0
    return {
        "total_pages": total_pages,
        "pages_with_issues": pages_with_issues,
        "pages_without_issues": total_pages - pages_with_issues,
        "pct_with_issues": pct,
        "critical_issues": crawl.critical_issues,
        "warning_issues": crawl.warning_issues,
        "info_issues": crawl.info_issues,
    }


# ---------------------------------------------------------------------------
# v0.5.0: Accessibility Analytics (WCAG 2.1 / BFSG)
# ---------------------------------------------------------------------------

ACCESSIBILITY_CATEGORIES = {
    # issue_type prefix -> WCAG category
    "a11y_missing_alt": "Perceivable",
    "a11y_empty_alt": "Perceivable",
    "a11y_missing_captions": "Perceivable",
    "a11y_missing_lang": "Perceivable",
    "a11y_invalid_lang": "Perceivable",
    "a11y_viewport_no_scale": "Perceivable",
    "a11y_viewport_limited_scale": "Perceivable",
    "a11y_vague_link": "Operable",
    "a11y_empty_link": "Operable",
    "a11y_icon_link": "Operable",
    "a11y_missing_skip": "Operable",
    "a11y_positive_tabindex": "Operable",
    "a11y_input_missing": "Understandable",
    "a11y_button_missing": "Understandable",
    "a11y_select_missing": "Understandable",
    "a11y_duplicate_ids": "Robust",
    "a11y_missing_title": "Robust",
    "bfsg_missing": "BFSG",
}


def _get_wcag_category(issue_type: str) -> str:
    for prefix, cat in ACCESSIBILITY_CATEGORIES.items():
        if issue_type.startswith(prefix):
            return cat
    return "Other"




def _get_wcag_level(issue_type: str) -> str:
    # Parse WCAG level A/AA/AAA from v0.6.0 issue_type prefix
    it = issue_type.lower()
    if it.startswith("wcag_aaa_"): return "AAA"
    if it.startswith("wcag_aa_"):  return "AA"
    if it.startswith("wcag_a_"):   return "A"
    legacy_aa = {"a11y_viewport_no_scale", "a11y_viewport_limited_scale",
                 "a11y_vague_link", "a11y_empty_link", "a11y_icon_link",
                 "a11y_missing_captions"}
    if issue_type in legacy_aa: return "AA"
    return "A"


def _get_wcag_principle(issue_type: str) -> str:
    # Parse WCAG principle from v0.6.0 issue_type
    parts = issue_type.split("_")
    if len(parts) >= 4 and parts[0].lower() == "wcag":
        code = parts[3] if len(parts) > 3 else ""
        if code and code[0].isdigit():
            p = code[0]
            if p == "1": return "perceivable"
            if p == "2": return "operable"
            if p == "3": return "understandable"
            if p == "4": return "robust"
    legacy = [
        ("a11y_missing_alt", "perceivable"), ("a11y_empty_alt", "perceivable"),
        ("a11y_missing_captions", "perceivable"), ("a11y_missing_lang", "perceivable"),
        ("a11y_invalid_lang", "perceivable"), ("a11y_viewport", "perceivable"),
        ("a11y_vague_link", "operable"), ("a11y_empty_link", "operable"),
        ("a11y_icon_link", "operable"), ("a11y_missing_skip", "operable"),
        ("a11y_positive_tabindex", "operable"),
        ("a11y_input_missing", "understandable"), ("a11y_button_missing", "understandable"),
        ("a11y_select_missing", "understandable"),
        ("a11y_duplicate_ids", "robust"), ("a11y_missing_title", "robust"),
        ("bfsg_", "perceivable"),
    ]
    for prefix, principle in legacy:
        if issue_type.startswith(prefix): return principle
    return "other"


def _calc_level_score(issues: list, total_pages: int) -> int:
    # Calculate 0-100 score for a subset of issues
    if total_pages == 0: return 100
    n_crit = sum(1 for i in issues if i.severity.value == "critical")
    n_warn = sum(1 for i in issues if i.severity.value == "warning")
    n_info = sum(1 for i in issues if i.severity.value == "info")
    deduction = min(n_crit * 4, 60) + min(n_warn * 2, 30) + min(n_info * 0.5, 10)
    return max(0, round(100 - deduction))

@router.get("/projects/{project_id}/analytics/accessibility")
def accessibility_analytics(
    project_id: int,
    crawl_id: int = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """v0.5.0: WCAG 2.1 / BFSG accessibility analytics for a project.

    Returns WCAG score (0-100), issues by category, top affected URLs.
    Uses the most recent completed crawl unless crawl_id is specified.
    """
    from ..models import Project, CrawlStatus

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    # Resolve crawl
    if crawl_id:
        crawl = db.query(Crawl).filter(
            Crawl.id == crawl_id, Crawl.project_id == project_id
        ).first()
        if not crawl:
            raise HTTPException(404, "Crawl not found for this project")
    else:
        crawl = (
            db.query(Crawl)
            .filter(
                Crawl.project_id == project_id,
                Crawl.status == CrawlStatus.COMPLETED,
            )
            .order_by(Crawl.completed_at.desc())
            .first()
        )
        if not crawl:
            return {
                "project_id": project_id,
                "crawl_id": None,
                "wcag_score": None,
                "total_pages": 0,
                "accessibility_issues": 0,
                "issues_by_category": {},
                "issues_by_severity": {"critical": 0, "warning": 0, "info": 0},
                "top_affected_urls": [],
                "bfsg_checklist": _bfsg_checklist({}),
                "message": "No completed crawl found for this project",
            }

    cid = crawl.id
    total_pages = db.query(Page).filter(Page.crawl_id == cid).count()

    # All accessibility issues for this crawl
    a11y_issues = (
        db.query(Issue)
        .filter(Issue.crawl_id == cid, Issue.category == "accessibility")
        .all()
    )

    # Count by severity
    n_critical = sum(1 for i in a11y_issues if i.severity.value == "critical")
    n_warning = sum(1 for i in a11y_issues if i.severity.value == "warning")
    n_info = sum(1 for i in a11y_issues if i.severity.value == "info")
    total_a11y = len(a11y_issues)

    # -----------------------------------------------------------------------
    # WCAG Score (0–100)
    # Deduct points based on issue density (issues per page), capped at 100
    # critical: -4 pts each (max -60), warning: -2 pts each (max -30), info: -0.5 (max -10)
    # -----------------------------------------------------------------------
    if total_pages == 0:
        wcag_score = 100
    else:
        deduction = (
            min(n_critical * 4, 60)
            + min(n_warning * 2, 30)
            + min(n_info * 0.5, 10)
        )
        wcag_score = max(0, round(100 - deduction))

    # Issues grouped by WCAG category
    category_counts: Dict[str, Dict] = {}
    WCAG_CATS = ["Perceivable", "Operable", "Understandable", "Robust", "BFSG", "Other"]
    for cat in WCAG_CATS:
        category_counts[cat] = {"critical": 0, "warning": 0, "info": 0, "total": 0}

    for issue in a11y_issues:
        cat = _get_wcag_category(issue.issue_type)
        sev = issue.severity.value
        category_counts[cat][sev] = category_counts[cat].get(sev, 0) + 1
        category_counts[cat]["total"] += 1

    # Per-category score (0-100): start 100, deduct by density
    for cat, counts in category_counts.items():
        if total_pages == 0:
            counts["score"] = 100
        else:
            cat_deduction = (
                min(counts["critical"] * 5, 70)
                + min(counts["warning"] * 2, 25)
                + min(counts["info"] * 0.5, 5)
            )
            counts["score"] = max(0, round(100 - cat_deduction))

    # Issues grouped by issue_type (for detailed breakdown)
    type_counts: Dict[str, Dict] = {}
    for issue in a11y_issues:
        key = issue.issue_type
        if key not in type_counts:
            type_counts[key] = {
                "issue_type": key,
                "description": issue.description,
                "recommendation": issue.recommendation or "",
                "category": _get_wcag_category(key),
                "critical": 0,
                "warning": 0,
                "info": 0,
                "total": 0,
            }
        sev = issue.severity.value
        type_counts[key][sev] += 1
        type_counts[key]["total"] += 1

    issues_by_type = sorted(
        type_counts.values(), key=lambda x: (x["critical"] * 3 + x["warning"] * 2 + x["info"]), reverse=True
    )

    # Top affected URLs (pages with most accessibility issues)
    page_issue_counts = {}
    for issue in a11y_issues:
        pid = issue.page_id
        if pid not in page_issue_counts:
            page_issue_counts[pid] = {"critical": 0, "warning": 0, "info": 0, "total": 0}
        sev = issue.severity.value
        page_issue_counts[pid][sev] = page_issue_counts[pid].get(sev, 0) + 1
        page_issue_counts[pid]["total"] += 1

    top_page_ids = sorted(page_issue_counts, key=lambda x: page_issue_counts[x]["total"], reverse=True)[:10]
    top_affected_urls = []
    for pid in top_page_ids:
        page = db.query(Page).filter(Page.id == pid).first()
        if page:
            top_affected_urls.append({
                "page_id": pid,
                "url": page.url,
                "title": page.title,
                "status_code": page.status_code,
                "critical": page_issue_counts[pid]["critical"],
                "warning": page_issue_counts[pid]["warning"],
                "info": page_issue_counts[pid]["info"],
                "total": page_issue_counts[pid]["total"],
            })

    # BFSG compliance checklist - derived from issue presence
    issue_types_present = {i.issue_type for i in a11y_issues}
    bfsg = _bfsg_checklist(issue_types_present)

    # v0.6.0: level-based scoring + principle breakdown
    issues_by_level_map: Dict[str, list] = {"A": [], "AA": [], "AAA": []}
    issues_by_principle_map: Dict[str, int] = {
        "perceivable": 0, "operable": 0, "understandable": 0, "robust": 0, "other": 0
    }
    for _iss in a11y_issues:
        _lvl = _get_wcag_level(_iss.issue_type)
        if _lvl in issues_by_level_map:
            issues_by_level_map[_lvl].append(_iss)
        _prin = _get_wcag_principle(_iss.issue_type)
        issues_by_principle_map[_prin] = issues_by_principle_map.get(_prin, 0) + 1

    score_a   = _calc_level_score(issues_by_level_map["A"],   total_pages)
    score_aa  = _calc_level_score(issues_by_level_map["AA"],  total_pages)
    score_aaa = _calc_level_score(issues_by_level_map["AAA"], total_pages)

    def _level_stats(lvl_issues: list) -> dict:
        return {
            "count":    len(lvl_issues),
            "critical": sum(1 for i in lvl_issues if i.severity.value == "critical"),
            "warning":  sum(1 for i in lvl_issues if i.severity.value == "warning"),
            "info":     sum(1 for i in lvl_issues if i.severity.value == "info"),
        }

    issues_by_level = {
        "A":   {**_level_stats(issues_by_level_map["A"]),   "score": score_a},
        "AA":  {**_level_stats(issues_by_level_map["AA"]),  "score": score_aa},
        "AAA": {**_level_stats(issues_by_level_map["AAA"]), "score": score_aaa},
    }

    def _has_blockers(lvl: str) -> bool:
        return any(i.severity.value in ("critical", "warning")
                   for i in issues_by_level_map[lvl])

    conformance_level = None
    if not _has_blockers("A"):
        conformance_level = "A"
        if not _has_blockers("AA"):
            conformance_level = "AA"
            if not _has_blockers("AAA"):
                conformance_level = "AAA"

    bfsg_blockers = sum(
        1 for i in a11y_issues
        if i.severity.value in ("critical", "warning")
        and (i.issue_type.startswith("bfsg_") or _get_wcag_level(i.issue_type) == "A")
    )
    bfsg_compliant = (bfsg_blockers == 0)

    return {
        "project_id": project_id,
        "crawl_id": cid,
        "crawl_completed_at": crawl.completed_at.isoformat() if crawl.completed_at else None,
        "wcag_version": "2.2",
        "wcag_score": wcag_score,
        "score_a": score_a,
        "score_aa": score_aa,
        "score_aaa": score_aaa,
        "conformance_level": conformance_level,
        "bfsg_compliant": bfsg_compliant,
        "total_pages": total_pages,
        "accessibility_issues": total_a11y,
        "issues_by_severity": {
            "critical": n_critical,
            "warning": n_warning,
            "info": n_info,
        },
        "issues_by_level": issues_by_level,
        "issues_by_principle": issues_by_principle_map,
        "issues_by_category": category_counts,
        "issues_by_type": issues_by_type,
        "top_affected_urls": top_affected_urls,
        "bfsg_checklist": bfsg,
        "score_label": _wcag_score_label(wcag_score),
    }



def _wcag_score_label(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 50:
        return "needs_improvement"
    return "poor"


def _bfsg_checklist(issue_types_present: set) -> List[Dict[str, Any]]:
    """Return BFSG compliance checklist items with pass/fail status."""
    checks = [
        {
            "id": "wcag_lang",
            "title": "Sprache ausgezeichnet (WCAG 3.1.1)",
            "description": "Das <html>-Tag hat ein gueltiges lang-Attribut",
            "passed": "a11y_missing_lang" not in issue_types_present
                      and "a11y_invalid_lang" not in issue_types_present,
            "wcag": "3.1.1",
            "level": "A",
        },
        {
            "id": "wcag_alt_text",
            "title": "Alternativtexte fuer Bilder (WCAG 1.1.1)",
            "description": "Alle Nicht-dekorations-Bilder haben Alt-Text",
            "passed": "a11y_missing_alt_text" not in issue_types_present,
            "wcag": "1.1.1",
            "level": "A",
        },
        {
            "id": "wcag_title",
            "title": "Seitentitel vorhanden (WCAG 2.4.2)",
            "description": "Jede Seite hat einen beschreibenden <title>-Tag",
            "passed": "a11y_missing_title" not in issue_types_present,
            "wcag": "2.4.2",
            "level": "A",
        },
        {
            "id": "wcag_form_labels",
            "title": "Formularbeschriftungen (WCAG 1.3.1)",
            "description": "Alle Formularfelder haben zugeordnete Labels",
            "passed": "a11y_input_missing_label" not in issue_types_present,
            "wcag": "1.3.1 / 3.3.2",
            "level": "A",
        },
        {
            "id": "wcag_buttons",
            "title": "Schaltflaechen beschriftet (WCAG 4.1.2)",
            "description": "Alle Schaltflaechen haben erkennbaren Text oder aria-label",
            "passed": "a11y_button_missing_label" not in issue_types_present,
            "wcag": "4.1.2",
            "level": "A",
        },
        {
            "id": "wcag_links",
            "title": "Aussagekraeftige Linktexte (WCAG 2.4.4)",
            "description": "Keine leeren oder vagen Link-Texte wie 'hier klicken'",
            "passed": "a11y_empty_link" not in issue_types_present
                      and "a11y_vague_link_text" not in issue_types_present,
            "wcag": "2.4.4",
            "level": "AA",
        },
        {
            "id": "wcag_zoom",
            "title": "Zoom nicht gesperrt (WCAG 1.4.4)",
            "description": "Viewport erlaubt Zoom (kein user-scalable=no)",
            "passed": "a11y_viewport_no_scale" not in issue_types_present,
            "wcag": "1.4.4",
            "level": "AA",
        },
        {
            "id": "wcag_skip_nav",
            "title": "Skip-Navigation vorhanden (WCAG 2.4.1)",
            "description": "Seiten haben einen 'Zum Hauptinhalt springen' Link",
            "passed": "a11y_missing_skip_nav" not in issue_types_present,
            "wcag": "2.4.1",
            "level": "A",
        },
        {
            "id": "bfsg_contact",
            "title": "Kontaktinformationen (BFSG)",
            "description": "Kontaktmoeglichkeit (tel:/mailto:) ist vorhanden",
            "passed": "bfsg_missing_contact" not in issue_types_present,
            "wcag": "BFSG",
            "level": "BFSG",
        },
        {
            "id": "bfsg_impressum",
            "title": "Impressum-Link (TMG/BFSG)",
            "description": "Sichtbarer Link zum Impressum ist vorhanden",
            "passed": "bfsg_missing_impressum" not in issue_types_present,
            "wcag": "BFSG / TMG",
            "level": "BFSG",
        },
        {
            "id": "bfsg_a11y_statement",
            "title": "Barrierefreiheitserklaerung (BFSG §12)",
            "description": "Link zur Barrierefreiheitserklaerung vorhanden (Pflicht ab 28.06.2025)",
            "passed": "bfsg_missing_a11y_statement" not in issue_types_present,
            "wcag": "BFSG §12",
            "level": "BFSG",
        },
    ]
    total = len(checks)
    passed = sum(1 for c in checks if c["passed"])
    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "compliance_pct": round(passed / total * 100) if total > 0 else 0,
    }


# ---------------------------------------------------------------------------
# v0.5.0: Performance Analytics
# ---------------------------------------------------------------------------

@router.get("/crawls/{crawl_id}/analytics/performance")
def performance_analytics(
    crawl_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """v0.5.0: Performance scoring distribution and statistics."""
    _get_crawl_or_404(crawl_id, db)

    pages_200 = db.query(Page).filter(
        Page.crawl_id == crawl_id,
        Page.status_code == 200,
        Page.performance_score.isnot(None),
    ).all()

    if not pages_200:
        return {
            "crawl_id": crawl_id,
            "total_scored": 0,
            "avg_score": None,
            "distribution": {"good": 0, "ok": 0, "poor": 0},
            "slow_pages": [],
        }

    scores = [p.performance_score for p in pages_200]
    avg_score = round(sum(scores) / len(scores))

    good = sum(1 for s in scores if s >= 80)
    ok = sum(1 for s in scores if 50 <= s < 80)
    poor = sum(1 for s in scores if s < 50)

    slow_pages = sorted(
        [p for p in pages_200 if p.performance_score < 50],
        key=lambda p: p.performance_score
    )[:10]

    return {
        "crawl_id": crawl_id,
        "total_scored": len(scores),
        "avg_score": avg_score,
        "score_label": _wcag_score_label(avg_score),
        "distribution": {
            "good": good,
            "ok": ok,
            "poor": poor,
        },
        "distribution_pct": {
            "good": round(good / len(scores) * 100, 1) if scores else 0,
            "ok": round(ok / len(scores) * 100, 1) if scores else 0,
            "poor": round(poor / len(scores) * 100, 1) if scores else 0,
        },
        "slow_pages": [
            {
                "page_id": p.id,
                "url": p.url,
                "title": p.title,
                "performance_score": p.performance_score,
                "response_time_ms": round(p.response_time * 1000, 1) if p.response_time else None,
            }
            for p in slow_pages
        ],
    }
