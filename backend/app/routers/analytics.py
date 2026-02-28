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
