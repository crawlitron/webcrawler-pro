from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import Crawl, Page, Issue, CrawlStatus, IssueSeverity

router = APIRouter(tags=["compare"])


@router.get("/api/projects/{project_id}/crawls")
def list_project_crawls(project_id: int, db: Session = Depends(get_db)):
    """List all crawls for a project with summary stats."""
    crawls = (
        db.query(Crawl)
        .filter(Crawl.project_id == project_id)
        .order_by(Crawl.created_at.desc())
        .all()
    )
    result = []
    for c in crawls:
        result.append({
            "id": c.id,
            "status": c.status,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
            "url_count": c.crawled_urls,
            "issue_count": c.critical_issues + c.warning_issues + c.info_issues,
            "critical_issues": c.critical_issues,
            "warning_issues": c.warning_issues,
            "info_issues": c.info_issues,
        })
    return result


@router.get("/api/compare/{crawl_a_id}/{crawl_b_id}")
def compare_crawls(crawl_a_id: int, crawl_b_id: int, db: Session = Depends(get_db)):
    """Diff two crawls and return structured comparison."""
    crawl_a = db.query(Crawl).filter(Crawl.id == crawl_a_id).first()
    crawl_b = db.query(Crawl).filter(Crawl.id == crawl_b_id).first()

    if not crawl_a:
        raise HTTPException(status_code=404, detail="Crawl A not found")
    if not crawl_b:
        raise HTTPException(status_code=404, detail="Crawl B not found")

    # Get pages for both crawls (url -> page data)
    def get_pages_map(crawl_id: int):
        pages = db.query(Page).filter(Page.crawl_id == crawl_id).all()
        return {p.url: p for p in pages}

    def get_issues_map(crawl_id: int):
        """Returns {url -> list of issue dicts}"""
        issues = (
            db.query(Issue, Page.url)
            .join(Page, Issue.page_id == Page.id)
            .filter(Issue.crawl_id == crawl_id)
            .all()
        )
        result = {}
        for issue, url in issues:
            if url not in result:
                result[url] = []
            result[url].append({
                "url": url,
                "type": issue.issue_type,
                "severity": issue.severity.value if hasattr(issue.severity, 'value') else issue.severity,
                "description": issue.description,
                "category": issue.category,
            })
        return result

    pages_a = get_pages_map(crawl_a_id)
    pages_b = get_pages_map(crawl_b_id)
    issues_a = get_issues_map(crawl_a_id)
    issues_b = get_issues_map(crawl_b_id)

    urls_a = set(pages_a.keys())
    urls_b = set(pages_b.keys())

    new_urls = sorted(urls_b - urls_a)[:500]
    removed_urls = sorted(urls_a - urls_b)[:500]
    common_urls = urls_a & urls_b

    # Issue sets as frozensets of (url, type) tuples for diff
    def issue_key_set(issues_map):
        s = set()
        for url, issue_list in issues_map.items():
            for iss in issue_list:
                s.add((url, iss["type"]))
        return s

    issue_keys_a = issue_key_set(issues_a)
    issue_keys_b = issue_key_set(issues_b)

    fixed_keys = issue_keys_a - issue_keys_b
    new_issue_keys = issue_keys_b - issue_keys_a

    # Build fixed_issues list
    fixed_issues = []
    for url, itype in sorted(fixed_keys)[:200]:
        for iss in issues_a.get(url, []):
            if iss["type"] == itype:
                fixed_issues.append({"url": url, "type": itype, "severity": iss["severity"]})
                break

    # Build new_issues list
    new_issues_list = []
    for url, itype in sorted(new_issue_keys)[:200]:
        for iss in issues_b.get(url, []):
            if iss["type"] == itype:
                new_issues_list.append({"url": url, "type": itype, "severity": iss["severity"], "description": iss["description"]})
                break

    # Status changes
    status_changes = []
    for url in common_urls:
        old_s = pages_a[url].status_code
        new_s = pages_b[url].status_code
        if old_s != new_s:
            status_changes.append({"url": url, "old_status": old_s, "new_status": new_s})
    status_changes = sorted(status_changes, key=lambda x: x["url"])[:200]

    # Title changes
    title_changes = []
    for url in common_urls:
        old_t = pages_a[url].title or ""
        new_t = pages_b[url].title or ""
        if old_t != new_t:
            title_changes.append({"url": url, "old": old_t, "new": new_t})
    title_changes = sorted(title_changes, key=lambda x: x["url"])[:200]

    # Performance changes
    performance_changes = []
    for url in common_urls:
        old_p = pages_a[url].performance_score
        new_p = pages_b[url].performance_score
        if old_p is not None and new_p is not None and old_p != new_p:
            performance_changes.append({"url": url, "old_score": old_p, "new_score": new_p})
    performance_changes = sorted(performance_changes, key=lambda x: abs(x["new_score"] - x["old_score"]), reverse=True)[:200]

    # Improved/degraded pages (by issue count)
    def count_issues_for_url(issues_map, url):
        return len(issues_map.get(url, []))

    improved_pages = 0
    degraded_pages = 0
    for url in common_urls:
        cnt_a = count_issues_for_url(issues_a, url)
        cnt_b = count_issues_for_url(issues_b, url)
        if cnt_b < cnt_a:
            improved_pages += 1
        elif cnt_b > cnt_a:
            degraded_pages += 1

    issue_count_a = crawl_a.critical_issues + crawl_a.warning_issues + crawl_a.info_issues
    issue_count_b = crawl_b.critical_issues + crawl_b.warning_issues + crawl_b.info_issues

    return {
        "crawl_a": {
            "id": crawl_a.id,
            "started_at": crawl_a.started_at.isoformat() if crawl_a.started_at else None,
            "url_count": crawl_a.crawled_urls,
            "issue_count": issue_count_a,
            "critical_issues": crawl_a.critical_issues,
        },
        "crawl_b": {
            "id": crawl_b.id,
            "started_at": crawl_b.started_at.isoformat() if crawl_b.started_at else None,
            "url_count": crawl_b.crawled_urls,
            "issue_count": issue_count_b,
            "critical_issues": crawl_b.critical_issues,
        },
        "summary": {
            "new_urls": len(new_urls),
            "removed_urls": len(removed_urls),
            "fixed_issues": len(fixed_issues),
            "new_issues": len(new_issues_list),
            "improved_pages": improved_pages,
            "degraded_pages": degraded_pages,
        },
        "new_urls": new_urls,
        "removed_urls": removed_urls,
        "new_issues": new_issues_list,
        "fixed_issues": fixed_issues,
        "status_changes": status_changes,
        "title_changes": title_changes,
        "performance_changes": performance_changes,
    }
