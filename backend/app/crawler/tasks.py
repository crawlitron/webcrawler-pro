
import os
import logging
from datetime import datetime
from multiprocessing import Process, Queue

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "webcrawler",
    broker=REDIS_URL,
    backend=REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

logger = logging.getLogger(__name__)


def _run_spider(start_url: str, max_urls: int, q: Queue):
    """Run Scrapy in a child process (Twisted reactor can only start once)."""
    import logging as _log
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.log import configure_logging
    from app.crawler.spider import SEOSpider

    configure_logging(install_root_handler=False)
    _log.basicConfig(level=_log.WARNING)

    results = []

    def collect(data):
        results.append(data)

    settings = {
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 8,
        "DOWNLOAD_DELAY": 0.1,
        "COOKIES_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
        "LOG_ENABLED": False,
        "REDIRECT_ENABLED": True,
        "REDIRECT_MAX_TIMES": 5,
        "HTTPERROR_ALLOW_ALL": True,
        "USER_AGENT": "WebCrawlerPro/1.0",
        "DOWNLOAD_TIMEOUT": 15,
        "DEPTH_LIMIT": 10,
    }
    proc = CrawlerProcess(settings)
    proc.crawl(SEOSpider, start_url=start_url, max_urls=max_urls, page_callback=collect)
    proc.start()
    q.put(results)


@celery_app.task(bind=True, name="tasks.run_crawl", max_retries=1)
def run_crawl(self, crawl_id: int, start_url: str, max_urls: int):
    """Celery task: crawl a site and store results in PostgreSQL."""
    from app.database import SessionLocal
    from app.models import Crawl, Page, Issue, CrawlStatus, IssueSeverity
    from app.crawler.analyzer import SEOAnalyzer

    db = SessionLocal()
    analyzer = SEOAnalyzer()

    try:
        crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()
        if not crawl:
            return
        crawl.status = CrawlStatus.RUNNING
        crawl.started_at = datetime.utcnow()
        crawl.celery_task_id = self.request.id
        db.commit()

        # Run spider in subprocess
        q = Queue()
        p = Process(target=_run_spider, args=(start_url, max_urls, q))
        p.start()
        p.join(timeout=3600)
        if p.exitcode != 0:
            raise RuntimeError(f"Spider process exited with code {p.exitcode}")
        if q.empty():
            raise RuntimeError("Spider returned no results")

        pages_data = q.get()
        logger.info(f"Crawl {crawl_id}: spider returned {len(pages_data)} pages")

        db.expire_all()
        crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()

        n_critical = n_warning = n_info = n_crawled = n_failed = 0

        for i, pd in enumerate(pages_data):
            try:
                sc = pd.get("status_code")
                if sc is None:
                    n_failed += 1
                else:
                    n_crawled += 1

                page = Page(
                    crawl_id=crawl_id,
                    url=pd["url"],
                    status_code=sc,
                    content_type=pd.get("content_type"),
                    response_time=pd.get("response_time"),
                    title=pd.get("title"),
                    meta_description=pd.get("meta_description"),
                    h1=pd.get("h1"),
                    h2_count=pd.get("h2_count", 0),
                    canonical_url=pd.get("canonical_url"),
                    internal_links_count=pd.get("internal_links_count", 0),
                    external_links_count=pd.get("external_links_count", 0),
                    images_without_alt=pd.get("images_without_alt", 0),
                    word_count=pd.get("word_count", 0),
                    is_indexable=pd.get("is_indexable", True),
                    redirect_url=pd.get("redirect_url"),
                    depth=pd.get("depth", 0),
                    extra_data={"h1_count": pd.get("h1_count", 0)},
                )
                db.add(page)
                db.flush()

                for issue in analyzer.analyze(pd):
                    db.add(Issue(
                        crawl_id=crawl_id,
                        page_id=page.id,
                        severity=IssueSeverity(issue.severity),
                        issue_type=issue.issue_type,
                        description=issue.description,
                        recommendation=issue.recommendation,
                    ))
                    if issue.severity == "critical":
                        n_critical += 1
                    elif issue.severity == "warning":
                        n_warning += 1
                    else:
                        n_info += 1

                if i % 10 == 0:
                    crawl.crawled_urls = n_crawled
                    crawl.failed_urls = n_failed
                    crawl.total_urls = len(pages_data)
                    crawl.critical_issues = n_critical
                    crawl.warning_issues = n_warning
                    crawl.info_issues = n_info
                    db.commit()

            except Exception as e:
                logger.error(f"Error processing page {pd.get('url')}: {e}")
                db.rollback()

        crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()
        crawl.status = CrawlStatus.COMPLETED
        crawl.completed_at = datetime.utcnow()
        crawl.crawled_urls = n_crawled
        crawl.failed_urls = n_failed
        crawl.total_urls = len(pages_data)
        crawl.critical_issues = n_critical
        crawl.warning_issues = n_warning
        crawl.info_issues = n_info
        db.commit()
        return {"status": "completed", "pages": n_crawled}

    except Exception as e:
        logger.error(f"Crawl {crawl_id} failed: {e}")
        try:
            db.rollback()
            crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()
            if crawl:
                crawl.status = CrawlStatus.FAILED
                crawl.error_message = str(e)
                crawl.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
