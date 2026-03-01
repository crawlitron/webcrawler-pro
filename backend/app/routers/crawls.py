import logging
logger = logging.getLogger(__name__)

import csv
import io
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db
from ..models import Project, Crawl, Page, CrawlStatus
from ..schemas import CrawlResponse

router = APIRouter(prefix="/api", tags=["crawls"])


def _to_response(crawl: Crawl) -> CrawlResponse:
    progress = None
    if crawl.status == CrawlStatus.COMPLETED:
        progress = 100.0
    elif crawl.status == CrawlStatus.PENDING:
        progress = 0.0
    elif crawl.total_urls and crawl.total_urls > 0:
        progress = round(crawl.crawled_urls / crawl.total_urls * 100, 1)
    return CrawlResponse(
        id=crawl.id, project_id=crawl.project_id, status=crawl.status,
        celery_task_id=crawl.celery_task_id, total_urls=crawl.total_urls,
        crawled_urls=crawl.crawled_urls, failed_urls=crawl.failed_urls,
        critical_issues=crawl.critical_issues, warning_issues=crawl.warning_issues,
        info_issues=crawl.info_issues, started_at=crawl.started_at,
        completed_at=crawl.completed_at, created_at=crawl.created_at,
        error_message=crawl.error_message, progress_percent=progress,
    )


@router.post("/projects/{project_id}/crawls", response_model=CrawlResponse, status_code=201)
def start_crawl(project_id: int, db: Session = Depends(get_db)):
    import json as _json
    from app.crawler.tasks import run_crawl
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(404, "Project not found")
    running = db.query(Crawl).filter(
        Crawl.project_id == project_id, Crawl.status == CrawlStatus.RUNNING
    ).first()
    if running:
        raise HTTPException(409, "A crawl is already running for this project")
    # Parse pattern lists from JSON strings
    include_patterns = None
    exclude_patterns = None
    try:
        if proj.include_patterns:
            include_patterns = _json.loads(proj.include_patterns)
    except (ValueError, TypeError):
        include_patterns = None
    try:
        if proj.exclude_patterns:
            exclude_patterns = _json.loads(proj.exclude_patterns)
    except (ValueError, TypeError):
        exclude_patterns = None
    crawl = Crawl(project_id=project_id, status=CrawlStatus.PENDING)
    db.add(crawl)
    db.commit()
    db.refresh(crawl)
    task = run_crawl.delay(
        crawl.id,
        proj.start_url,
        proj.max_urls,
        custom_user_agent=proj.custom_user_agent,
        crawl_delay=proj.crawl_delay if proj.crawl_delay is not None else 0.5,
        include_patterns=include_patterns or [],
        exclude_patterns=exclude_patterns or [],
        crawl_external_links=proj.crawl_external_links or False,
    )
    crawl.celery_task_id = task.id
    db.commit()
    db.refresh(crawl)
    return _to_response(crawl)


@router.get("/crawls/{crawl_id}", response_model=CrawlResponse)
def get_crawl(crawl_id: int, db: Session = Depends(get_db)):
    c = db.query(Crawl).filter(Crawl.id == crawl_id).first()
    if not c:
        raise HTTPException(404, "Crawl not found")
    return _to_response(c)


@router.get("/projects/{project_id}/crawls", response_model=List[CrawlResponse])
def list_crawls(project_id: int, db: Session = Depends(get_db)):
    if not db.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    return [_to_response(c) for c in
            db.query(Crawl).filter(Crawl.project_id == project_id).order_by(desc(Crawl.created_at)).all()]


@router.get("/crawls/{crawl_id}/export/csv")
def export_csv(crawl_id: int, db: Session = Depends(get_db)):
    if not db.query(Crawl).filter(Crawl.id == crawl_id).first():
        raise HTTPException(404, "Crawl not found")
    pages = db.query(Page).filter(Page.crawl_id == crawl_id).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["URL", "Status", "Response Time", "Title", "Title Len",
                "Meta Description", "Meta Len", "H1", "H2 Count", "Canonical",
                "Internal Links", "External Links", "Images No Alt",
                "Word Count", "Indexable", "Redirect URL", "Depth", "Content Type"])
    for p in pages:
        w.writerow([
            p.url, p.status_code or "",
            f"{p.response_time:.3f}" if p.response_time else "",
            p.title or "", len(p.title) if p.title else 0,
            p.meta_description or "", len(p.meta_description) if p.meta_description else 0,
            p.h1 or "", p.h2_count, p.canonical_url or "",
            p.internal_links_count, p.external_links_count, p.images_without_alt,
            p.word_count, p.is_indexable, p.redirect_url or "", p.depth, p.content_type or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=crawl_{crawl_id}.csv"},
    )


@router.get("/crawls/{crawl_id}/export/json")
def export_json(crawl_id: int, db: Session = Depends(get_db)):
    """Export all crawl data as JSON."""
    import json as _json
    crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()
    if not crawl:
        raise HTTPException(404, "Crawl not found")
    pages = db.query(Page).filter(Page.crawl_id == crawl_id).all()
    data = {
        "crawl_id": crawl_id,
        "project_id": crawl.project_id,
        "status": crawl.status.value,
        "crawled_urls": crawl.crawled_urls,
        "total_urls": crawl.total_urls,
        "started_at": crawl.started_at.isoformat() if crawl.started_at else None,
        "completed_at": crawl.completed_at.isoformat() if crawl.completed_at else None,
        "pages": [
            {
                "url": p.url,
                "status_code": p.status_code,
                "content_type": p.content_type,
                "response_time": p.response_time,
                "title": p.title,
                "meta_description": p.meta_description,
                "h1": p.h1,
                "h2_count": p.h2_count,
                "canonical_url": p.canonical_url,
                "internal_links_count": p.internal_links_count,
                "external_links_count": p.external_links_count,
                "images_without_alt": p.images_without_alt,
                "word_count": p.word_count,
                "is_indexable": p.is_indexable,
                "redirect_url": p.redirect_url,
                "depth": p.depth,
                "crawled_at": p.crawled_at.isoformat() if p.crawled_at else None,
                "extra_data": p.extra_data,
            }
            for p in pages
        ],
    }
    content = _json.dumps(data, ensure_ascii=False, indent=2)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=crawl_{crawl_id}.json"},
    )


@router.get("/crawls/{crawl_id}/export/sitemap")
def export_sitemap(crawl_id: int, db: Session = Depends(get_db)):
    """Export sitemap.xml for all indexable 200-OK HTML pages."""
    from fastapi.responses import Response
    crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()
    if not crawl:
        raise HTTPException(404, "Crawl not found")
    pages = db.query(Page).filter(
        Page.crawl_id == crawl_id,
        Page.status_code == 200,
        Page.is_indexable == True,  # noqa: E712
        Page.content_type.like("%text/html%")
    ).order_by(Page.depth, Page.url).all()
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    priority_map = {0: "1.0", 1: "0.8", 2: "0.6"}
    for p in pages:
        lastmod = p.crawled_at.strftime("%Y-%m-%d") if p.crawled_at else ""
        priority = priority_map.get(p.depth, "0.4")
        safe_url = p.url.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        xml += "  <url>\n"
        xml += f"    <loc>{safe_url}</loc>\n"
        if lastmod:
            xml += f"    <lastmod>{lastmod}</lastmod>\n"
        xml += "    <changefreq>weekly</changefreq>\n"
        xml += f"    <priority>{priority}</priority>\n"
        xml += "  </url>\n"
    xml += "</urlset>"
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=sitemap_{crawl_id}.xml"},
    )


@router.post("/crawls/{crawl_id}/cancel")
def cancel_crawl(crawl_id: int, db: Session = Depends(get_db)):
    """Cancel a running or pending crawl."""
    import os as _os
    crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()
    if not crawl:
        raise HTTPException(404, "Crawl not found")
    if crawl.status not in (CrawlStatus.RUNNING, CrawlStatus.PENDING):
        raise HTTPException(409, f"Cannot cancel crawl in status: {crawl.status.value}")
    if crawl.celery_task_id:
        try:
            from celery import Celery
            celery_app = Celery(
                broker=_os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
            )
            celery_app.control.revoke(crawl.celery_task_id, terminate=True, signal="SIGTERM")
        except Exception as e:
            logger.warning("Failed to revoke Celery task: %s", e)
    from datetime import datetime
    crawl.status = CrawlStatus.FAILED
    crawl.error_message = "Cancelled by user"
    crawl.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(crawl)
    return _to_response(crawl)


@router.get("/crawls/{crawl_id}/links")
def get_links(
    crawl_id: int,
    link_type: str = None,
    status_code: int = None,
    nofollow: bool = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    """Get all found links (internal + external) with filters."""
    crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()
    if not crawl:
        raise HTTPException(404, "Crawl not found")
    pages_q = db.query(Page).filter(Page.crawl_id == crawl_id)
    if status_code is not None:
        pages_q = pages_q.filter(Page.status_code == status_code)
    all_pages = pages_q.all()
    links = []
    for p in all_pages:
        extra = p.extra_data or {}
        if link_type in (None, "internal"):
            for lnk in extra.get("internal_links", [])[:100]:
                lnk_nofollow = lnk.get("nofollow", False)
                if nofollow is not None and lnk_nofollow != nofollow:
                    continue
                links.append({
                    "source_url": p.url,
                    "target_url": lnk.get("url", ""),
                    "anchor_text": lnk.get("text", ""),
                    "link_type": "internal",
                    "nofollow": lnk_nofollow,
                    "status_code": lnk.get("status_code"),
                })
        if link_type in (None, "external"):
            for lnk in extra.get("external_links", [])[:50]:
                lnk_nofollow = lnk.get("nofollow", False)
                if nofollow is not None and lnk_nofollow != nofollow:
                    continue
                links.append({
                    "source_url": p.url,
                    "target_url": lnk.get("url", ""),
                    "anchor_text": lnk.get("text", ""),
                    "link_type": "external",
                    "nofollow": lnk_nofollow,
                    "status_code": lnk.get("status_code"),
                })
    total = len(links)
    start = (page - 1) * page_size
    end = start + page_size
    import math
    return {
        "items": links[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }
