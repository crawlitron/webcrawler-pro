import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, asc, desc
from ..database import get_db
from ..models import Crawl, Page, Issue, IssueSeverity
from ..schemas import PageResponse, PageListResponse, IssueResponse, IssueListResponse

router = APIRouter(prefix="/api/crawls", tags=["pages"])

SORT_COLUMNS = {
    "url": Page.url,
    "status_code": Page.status_code,
    "response_time": Page.response_time,
    "word_count": Page.word_count,
    "depth": Page.depth,
    "internal_links_count": Page.internal_links_count,
    "external_links_count": Page.external_links_count,
    "images_without_alt": Page.images_without_alt,
    "crawled_at": Page.crawled_at,
}


def _build_page_response(p: Page, issue_count: int) -> PageResponse:
    return PageResponse(
        id=p.id, crawl_id=p.crawl_id, url=p.url, status_code=p.status_code,
        content_type=p.content_type, response_time=p.response_time, title=p.title,
        meta_description=p.meta_description, h1=p.h1, h2_count=p.h2_count,
        canonical_url=p.canonical_url, internal_links_count=p.internal_links_count,
        external_links_count=p.external_links_count, images_without_alt=p.images_without_alt,
        word_count=p.word_count, is_indexable=p.is_indexable, redirect_url=p.redirect_url,
        depth=p.depth, crawled_at=p.crawled_at, issue_count=issue_count,
        extra_data=p.extra_data,
    )


@router.get("/{crawl_id}/pages", response_model=PageListResponse)
def get_pages(
    crawl_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status_code: Optional[int] = None,
    status_class: Optional[str] = None,   # "2xx", "3xx", "4xx", "5xx"
    content_type: Optional[str] = None,
    is_indexable: Optional[bool] = None,
    has_issues: Optional[bool] = None,
    issue_type: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("depth", description="Column to sort by"),
    sort_dir: Optional[str] = Query("asc", description="asc or desc"),
    db: Session = Depends(get_db),
):
    if not db.query(Crawl).filter(Crawl.id == crawl_id).first():
        raise HTTPException(404, "Crawl not found")

    q = db.query(Page).filter(Page.crawl_id == crawl_id)

    # --- Filters ---
    if status_code is not None:
        q = q.filter(Page.status_code == status_code)
    elif status_class:
        cls = status_class.lower().replace("xx", "")
        try:
            base = int(cls) * 100
            q = q.filter(Page.status_code >= base, Page.status_code < base + 100)
        except ValueError:
            pass

    if content_type:
        q = q.filter(Page.content_type.ilike("%" + content_type + "%"))

    if is_indexable is not None:
        q = q.filter(Page.is_indexable == is_indexable)

    if search:
        q = q.filter(Page.url.ilike("%" + search + "%"))

    if issue_type:
        q = q.join(Issue, Issue.page_id == Page.id).filter(Issue.issue_type == issue_type)

    if has_issues is True:
        q = q.filter(
            Page.id.in_(
                db.query(Issue.page_id).filter(Issue.crawl_id == crawl_id).distinct()
            )
        )
    elif has_issues is False:
        q = q.filter(
            Page.id.notin_(
                db.query(Issue.page_id).filter(Issue.crawl_id == crawl_id).distinct()
            )
        )

    # --- Sorting ---
    sort_col = SORT_COLUMNS.get(sort_by or "depth", Page.depth)
    if sort_dir and sort_dir.lower() == "desc":
        q = q.order_by(desc(sort_col), Page.url)
    else:
        q = q.order_by(asc(sort_col), Page.url)

    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    # Batch-load issue counts
    ids = [r.id for r in rows]
    counts = {}
    if ids:
        for pid, cnt in db.query(Issue.page_id, func.count(Issue.id)).filter(
                Issue.page_id.in_(ids)).group_by(Issue.page_id).all():
            counts[pid] = cnt

    items = [_build_page_response(p, counts.get(p.id, 0)) for p in rows]
    return PageListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{crawl_id}/pages/{page_id}", response_model=PageResponse)
def get_page_detail(crawl_id: int, page_id: int, db: Session = Depends(get_db)):
    """Get full detail of a single page including extra_data."""
    if not db.query(Crawl).filter(Crawl.id == crawl_id).first():
        raise HTTPException(404, "Crawl not found")
    p = db.query(Page).filter(Page.id == page_id, Page.crawl_id == crawl_id).first()
    if not p:
        raise HTTPException(404, "Page not found")
    cnt = db.query(func.count(Issue.id)).filter(Issue.page_id == page_id).scalar() or 0
    return _build_page_response(p, cnt)


@router.get("/{crawl_id}/pages/{page_id}/issues")
def get_page_issues(
    crawl_id: int,
    page_id: int,
    db: Session = Depends(get_db),
) -> List[IssueResponse]:
    """Get all issues for a specific page."""
    if not db.query(Crawl).filter(Crawl.id == crawl_id).first():
        raise HTTPException(404, "Crawl not found")
    p = db.query(Page).filter(Page.id == page_id, Page.crawl_id == crawl_id).first()
    if not p:
        raise HTTPException(404, "Page not found")
    issues = db.query(Issue).filter(
        Issue.page_id == page_id, Issue.crawl_id == crawl_id
    ).order_by(Issue.severity).all()
    return [
        IssueResponse(
            id=i.id, crawl_id=i.crawl_id, page_id=i.page_id, page_url=p.url,
            severity=i.severity, issue_type=i.issue_type,
            description=i.description, recommendation=i.recommendation,
        )
        for i in issues
    ]


@router.get("/{crawl_id}/issues", response_model=IssueListResponse)
def get_issues(
    crawl_id: int,
    severity: Optional[str] = None,
    issue_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if not db.query(Crawl).filter(Crawl.id == crawl_id).first():
        raise HTTPException(404, "Crawl not found")
    q = db.query(Issue, Page.url).join(
        Page, Issue.page_id == Page.id
    ).filter(Issue.crawl_id == crawl_id)
    if severity:
        try:
            q = q.filter(Issue.severity == IssueSeverity(severity))
        except ValueError:
            raise HTTPException(400, "Invalid severity: {}".format(severity))
    if issue_type:
        q = q.filter(Issue.issue_type == issue_type)
    q = q.order_by(Issue.severity, Issue.issue_type)
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    items, n_crit, n_warn, n_info = [], 0, 0, 0
    for issue, page_url in rows:
        items.append(IssueResponse(
            id=issue.id, crawl_id=issue.crawl_id, page_id=issue.page_id,
            page_url=page_url, severity=issue.severity,
            issue_type=issue.issue_type, description=issue.description,
            recommendation=issue.recommendation,
        ))
        if issue.severity == IssueSeverity.CRITICAL:
            n_crit += 1
        elif issue.severity == IssueSeverity.WARNING:
            n_warn += 1
        else:
            n_info += 1
    return IssueListResponse(items=items, total=total, critical=n_crit, warning=n_warn, info=n_info)
