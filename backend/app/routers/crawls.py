
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
    from app.crawler.tasks import run_crawl
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(404, "Project not found")
    running = db.query(Crawl).filter(
        Crawl.project_id == project_id, Crawl.status == CrawlStatus.RUNNING
    ).first()
    if running:
        raise HTTPException(409, "A crawl is already running for this project")
    crawl = Crawl(project_id=project_id, status=CrawlStatus.PENDING)
    db.add(crawl)
    db.commit()
    db.refresh(crawl)
    task = run_crawl.delay(crawl.id, proj.start_url, proj.max_urls)
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
    w.writerow(["URL","Status","Response Time","Title","Title Len",
                "Meta Description","Meta Len","H1","H2 Count","Canonical",
                "Internal Links","External Links","Images No Alt",
                "Word Count","Indexable","Redirect URL","Depth","Content Type"])
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
