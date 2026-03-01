from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Project, Crawl, CrawlStatus
from ..crawler.robots_sitemap import analyze_robots_txt, analyze_sitemap

router = APIRouter(prefix="/api/projects", tags=["seo-tools"])


def _get_project_base_url(project_id: int, db: Session) -> str:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.start_url


def _get_sitemap_urls_from_robots(base_url: str) -> list:
    """Returns sitemap URLs extracted from robots.txt."""
    try:
        robots = analyze_robots_txt(base_url)
        return robots.get("sitemaps", [])
    except Exception:
        return []


@router.get("/{project_id}/robots")
def get_robots(project_id: int, db: Session = Depends(get_db)):
    """Analyze robots.txt for a project's start URL."""
    base_url = _get_project_base_url(project_id, db)
    result = analyze_robots_txt(base_url)
    return result


@router.get("/{project_id}/sitemap")
def get_sitemap(project_id: int, db: Session = Depends(get_db)):
    """Analyze sitemap.xml for a project's start URL."""
    base_url = _get_project_base_url(project_id, db)
    # First try to get sitemap URL from robots.txt
    sitemap_urls = _get_sitemap_urls_from_robots(base_url)
    if sitemap_urls:
        sitemap_url = sitemap_urls[0]
    else:
        sitemap_url = base_url  # analyze_sitemap will try /sitemap.xml, /sitemap_index.xml
    result = analyze_sitemap(sitemap_url)
    return result


@router.get("/{project_id}/seo-tools")
def get_seo_tools(project_id: int, db: Session = Depends(get_db)):
    """Combined robots.txt + sitemap analysis, plus crawled URLs vs sitemap comparison."""
    base_url = _get_project_base_url(project_id, db)

    robots = analyze_robots_txt(base_url)

    sitemap_url = robots["sitemaps"][0] if robots["sitemaps"] else base_url
    sitemap = analyze_sitemap(sitemap_url)

    # Get latest completed crawl URLs for comparison
    from ..models import Page
    latest_crawl = (
        db.query(Crawl)
        .filter(Crawl.project_id == project_id, Crawl.status == CrawlStatus.COMPLETED)
        .order_by(Crawl.completed_at.desc())
        .first()
    )

    crawled_urls = set()
    if latest_crawl:
        pages = db.query(Page.url).filter(Page.crawl_id == latest_crawl.id).all()
        crawled_urls = {p.url for p in pages}

    sitemap_url_set = set(sitemap.get("urls", []))

    in_sitemap_not_crawled = sorted(sitemap_url_set - crawled_urls)[:500]
    crawled_not_in_sitemap = sorted(crawled_urls - sitemap_url_set)[:500]
    in_both = sorted(sitemap_url_set & crawled_urls)[:500]

    return {
        "robots": robots,
        "sitemap": sitemap,
        "url_comparison": {
            "crawled_count": len(crawled_urls),
            "sitemap_count": len(sitemap_url_set),
            "in_both": in_both,
            "in_both_count": len(sitemap_url_set & crawled_urls),
            "in_sitemap_not_crawled": in_sitemap_not_crawled,
            "in_sitemap_not_crawled_count": len(sitemap_url_set - crawled_urls),
            "crawled_not_in_sitemap": crawled_not_in_sitemap,
            "crawled_not_in_sitemap_count": len(crawled_urls - sitemap_url_set),
            "latest_crawl_id": latest_crawl.id if latest_crawl else None,
        },
    }
