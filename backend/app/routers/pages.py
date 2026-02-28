
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import Crawl, Page, Issue, IssueSeverity
from ..schemas import PageResponse, PageListResponse, IssueResponse, IssueListResponse

router = APIRouter(prefix="/api/crawls", tags=["pages"])


@router.get("/{crawl_id}/pages", response_model=PageListResponse)
def get_pages(
    crawl_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_code: Optional[int] = None,
    issue_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not db.query(Crawl).filter(Crawl.id == crawl_id).first():
        raise HTTPException(404, "Crawl not found")
    q = db.query(Page).filter(Page.crawl_id == crawl_id)
    if status_code is not None:
        q = q.filter(Page.status_code == status_code)
    if search:
        q = q.filter(Page.url.ilike(f"%{search}%"))
    if issue_type:
        q = q.join(Issue).filter(Issue.issue_type == issue_type)
    total = q.count()
    rows = q.order_by(Page.depth, Page.url).offset((page - 1) * page_size).limit(page_size).all()
    # issue counts
    ids = [r.id for r in rows]
    counts = {}
    if ids:
        for pid, cnt in db.query(Issue.page_id, func.count(Issue.id)).filter(
            Issue.page_id.in_(ids)).group_by(Issue.page_id).all():
            counts[pid] = cnt
    items = [PageResponse(
        id=p.id, crawl_id=p.crawl_id, url=p.url, status_code=p.status_code,
        content_type=p.content_type, response_time=p.response_time, title=p.title,
        meta_description=p.meta_description, h1=p.h1, h2_count=p.h2_count,
        canonical_url=p.canonical_url, internal_links_count=p.internal_links_count,
        external_links_count=p.external_links_count, images_without_alt=p.images_without_alt,
        word_count=p.word_count, is_indexable=p.is_indexable, redirect_url=p.redirect_url,
        depth=p.depth, crawled_at=p.crawled_at, issue_count=counts.get(p.id, 0),
    ) for p in rows]
    return PageListResponse(items=items, total=total, page=page, page_size=page_size,
                            total_pages=(total + page_size - 1) // page_size)


@router.get("/{crawl_id}/issues", response_model=IssueListResponse)
def get_issues(
    crawl_id: int,
    severity: Optional[str] = None,
    issue_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not db.query(Crawl).filter(Crawl.id == crawl_id).first():
        raise HTTPException(404, "Crawl not found")
    q = db.query(Issue, Page.url).join(Page, Issue.page_id == Page.id).filter(Issue.crawl_id == crawl_id)
    if severity:
        try:
            q = q.filter(Issue.severity == IssueSeverity(severity))
        except ValueError:
            raise HTTPException(400, f"Invalid severity: {severity}")
    if issue_type:
        q = q.filter(Issue.issue_type == issue_type)
    rows = q.order_by(Issue.severity, Issue.issue_type).all()
    items, n_crit, n_warn, n_info = [], 0, 0, 0
    for issue, page_url in rows:
        items.append(IssueResponse(
            id=issue.id, crawl_id=issue.crawl_id, page_id=issue.page_id,
            page_url=page_url, severity=issue.severity,
            issue_type=issue.issue_type, description=issue.description,
            recommendation=issue.recommendation,
        ))
        if issue.severity == IssueSeverity.CRITICAL:  n_crit += 1
        elif issue.severity == IssueSeverity.WARNING: n_warn += 1
        else:                                         n_info += 1
    return IssueListResponse(items=items, total=len(items), critical=n_crit, warning=n_warn, info=n_info)
