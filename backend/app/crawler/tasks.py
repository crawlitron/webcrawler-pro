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


def _run_spider(
    start_url: str,
    max_urls: int,
    q: Queue,
    custom_user_agent: str = None,
    crawl_delay: float = 0.5,
    include_patterns: list = None,
    exclude_patterns: list = None,
    crawl_external_links: bool = False,
):
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

    ua = custom_user_agent or "WebCrawlerPro/2.0 (+https://webcrawlerpro.io/bot)"

    settings = {
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 8,
        "DOWNLOAD_DELAY": crawl_delay,
        "COOKIES_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
        "LOG_ENABLED": False,
        "REDIRECT_ENABLED": True,
        "REDIRECT_MAX_TIMES": 10,
        "HTTPERROR_ALLOW_ALL": True,
        "USER_AGENT": ua,
        "DOWNLOAD_TIMEOUT": 15,
        "DEPTH_LIMIT": 10,
    }
    proc = CrawlerProcess(settings)
    proc.crawl(
        SEOSpider,
        start_url=start_url,
        max_urls=max_urls,
        page_callback=collect,
        custom_user_agent=custom_user_agent,
        crawl_delay=crawl_delay,
        include_patterns=include_patterns or [],
        exclude_patterns=exclude_patterns or [],
        crawl_external_links=crawl_external_links,
    )
    proc.start()
    q.put(results)


@celery_app.task(bind=True, name="tasks.run_crawl", max_retries=1)
def run_crawl(
    self,
    crawl_id: int,
    start_url: str,
    max_urls: int,
    custom_user_agent: str = None,
    crawl_delay: float = 0.5,
    include_patterns: list = None,
    exclude_patterns: list = None,
    crawl_external_links: bool = False,
):
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
        p = Process(
            target=_run_spider,
            args=(start_url, max_urls, q),
            kwargs={
                "custom_user_agent": custom_user_agent,
                "crawl_delay": crawl_delay,
                "include_patterns": include_patterns or [],
                "exclude_patterns": exclude_patterns or [],
                "crawl_external_links": crawl_external_links,
            },
        )
        p.start()
        p.join(timeout=3600)
        if p.exitcode != 0:
            raise RuntimeError("Spider process exited with code {}".format(p.exitcode))
        if q.empty():
            raise RuntimeError("Spider returned no results")

        pages_data = q.get()
        logger.info("Crawl %d: spider returned %d pages", crawl_id, len(pages_data))

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

                # Build extra_data - merge spider extra_data with redirect chain
                spider_extra = pd.get("extra_data") or {}
                redirect_chain = pd.get("redirect_chain", [])
                spider_extra["redirect_chain"] = redirect_chain
                spider_extra["redirect_hops"] = pd.get("redirect_hops", len(redirect_chain) - 1 if len(redirect_chain) > 1 else 0)
                spider_extra["h1_count"] = pd.get("h1_count", 0)

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
                    extra_data=spider_extra,
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
                logger.error("Error processing page %s: %s", pd.get("url"), e)
                db.rollback()

        # --- Post-crawl: Duplicate content detection ---
        try:
            dup_count = analyzer.analyze_duplicates(crawl_id, db)
            if dup_count > 0:
                logger.info("Crawl %d: found %d duplicate content issues", crawl_id, dup_count)
                # Re-count all warning issues (duplicates are warnings)
                from app.models import IssueSeverity as IS
                from sqlalchemy import func
                counts = db.query(
                    IS, func.count(Issue.id)
                ).filter(Issue.crawl_id == crawl_id).group_by(Issue.severity).all()
                n_critical = n_warning = n_info = 0
                for sev, cnt in counts:
                    if sev == IS.CRITICAL:
                        n_critical = cnt
                    elif sev == IS.WARNING:
                        n_warning = cnt
                    else:
                        n_info = cnt
        except Exception as e:
            logger.error("Duplicate analysis failed for crawl %d: %s", crawl_id, e)

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
        logger.error("Crawl %d failed: %s", crawl_id, e)
        try:
            db.rollback()
            crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()
            if crawl:
                crawl.status = CrawlStatus.FAILED
                crawl.error_message = str(e)
                crawl.completed_at = datetime.utcnow()
                db.commit()
        except Exception as e2:
            logger.warning("DB rollback failed: %s", e2)
        raise
    finally:
        db.close()
