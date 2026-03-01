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
    use_js_rendering: bool = False,
    js_wait_time: float = 2.0,
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
    # v0.8.0 Feature 1: Playwright JS rendering settings
    if use_js_rendering:
        settings.update({
            "DOWNLOAD_HANDLERS": {
                "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            },
            "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            "PLAYWRIGHT_BROWSER_TYPE": "chromium",
            "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True, "args": ["--no-sandbox"]},
        })
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
        use_js_rendering=use_js_rendering,
        js_wait_time=js_wait_time,
    )
    proc.start()
    q.put(results)


def _calculate_performance_score(pd: dict) -> int:
    """v0.5.0: Score 0-100 based on response time, status code, redirects, content."""
    score = 0
    status = pd.get("status_code") or 0
    rt = pd.get("response_time") or 0.0
    extra = pd.get("extra_data") or {}
    redirect_hops = extra.get("redirect_hops", 0) or 0
    word_count = pd.get("word_count", 0) or 0

    # Component 1: Response time (0-40 pts)
    if rt <= 0.2:
        score += 40
    elif rt <= 0.5:
        score += 30
    elif rt <= 1.0:
        score += 20
    elif rt <= 3.0:
        score += 10
    else:
        score += 0

    # Component 2: HTTP status (0-20 pts)
    if status == 200:
        score += 20
    elif 300 <= status < 400:
        score += 10
    else:
        score += 0

    # Component 3: No redirect chain (0-20 pts)
    if redirect_hops == 0:
        score += 20
    elif redirect_hops == 1:
        score += 12
    elif redirect_hops == 2:
        score += 5
    else:
        score += 0

    # Component 4: Content quality (0-20 pts)
    if word_count >= 300:
        score += 20
    elif word_count >= 100:
        score += 15
    elif word_count >= 50:
        score += 8
    else:
        score += 0

    return min(100, max(0, score))


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
    use_js_rendering: bool = False,
    js_wait_time: float = 2.0,
):
    """Celery task: crawl a site and store results in PostgreSQL."""
    from app.database import SessionLocal
    from app.models import Crawl, Page, Issue, CrawlStatus, IssueSeverity, Project
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
                "use_js_rendering": use_js_rendering,
                "js_wait_time": js_wait_time,
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

                # Build extra_data
                spider_extra = pd.get("extra_data") or {}
                redirect_chain = pd.get("redirect_chain", [])
                spider_extra["redirect_chain"] = redirect_chain
                spider_extra["redirect_hops"] = pd.get(
                    "redirect_hops",
                    len(redirect_chain) - 1 if len(redirect_chain) > 1 else 0
                )
                spider_extra["h1_count"] = pd.get("h1_count", 0)

                # v0.5.0: Keyword analysis — store in extra_data
                kw_data = analyzer.analyze_keywords(pd)
                if kw_data.get("top_keywords"):
                    spider_extra["keywords"] = kw_data
                # v0.9.0: Mobile-First SEO analysis — store in extra_data
                mobile_check = analyzer.analyze_mobile_seo(pd, soup=None)
                if mobile_check:
                    spider_extra["mobile_check"] = mobile_check

                # v0.5.0: Performance score
                perf_score = _calculate_performance_score(pd)

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
                    performance_score=perf_score,
                )
                db.add(page)
                db.flush()

                # SEO issues (category=seo)
                for issue in analyzer.analyze(pd):
                    cat = getattr(issue, "category", "seo") or "seo"
                    db.add(Issue(
                        crawl_id=crawl_id,
                        page_id=page.id,
                        severity=IssueSeverity(issue.severity),
                        issue_type=issue.issue_type,
                        description=issue.description,
                        recommendation=issue.recommendation,
                        category=cat,
                    ))
                    if issue.severity == "critical":
                        n_critical += 1
                    elif issue.severity == "warning":
                        n_warning += 1
                    else:
                        n_info += 1

                # v0.6.0: Accessibility issues (category=accessibility)
                # analyze_accessibility now returns list of dicts with WCAG 2.1+2.2 metadata
                for a11y_issue in analyzer.analyze_accessibility(pd):
                    if isinstance(a11y_issue, dict):
                        sev_str = a11y_issue.get("severity", "info")
                        issue_type_str = a11y_issue.get("type", "wcag_unknown")
                        desc = a11y_issue.get("description", "")
                        title = a11y_issue.get("title", "")
                        criterion = a11y_issue.get("wcag_criterion", "")
                        recommendation = (
                            f"{title} (WCAG {criterion})".strip(" (")
                            if criterion else title
                        )
                    else:
                        # Legacy SEOIssue namedtuple fallback
                        sev_str = a11y_issue.severity
                        issue_type_str = a11y_issue.issue_type
                        desc = a11y_issue.description
                        recommendation = getattr(a11y_issue, "recommendation", "") or ""
                    try:
                        sev_enum = IssueSeverity(sev_str)
                    except ValueError:
                        sev_enum = IssueSeverity.INFO
                    db.add(Issue(
                        crawl_id=crawl_id,
                        page_id=page.id,
                        severity=sev_enum,
                        issue_type=issue_type_str,
                        description=desc,
                        recommendation=recommendation,
                        category="accessibility",
                    ))
                    if sev_str == "critical":
                        n_critical += 1
                    elif sev_str == "warning":
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

        # --- Post-crawl v0.7.0: robots.txt + sitemap analysis ---
        try:
            from app.crawler.robots_sitemap import analyze_robots_txt, analyze_sitemap
            from app.models import Page as PageModel
            project = db.query(Project).filter(Project.id == crawl.project_id).first()
            if project:
                robots_result = analyze_robots_txt(project.start_url)
                sitemap_urls = robots_result.get("sitemaps", [])
                sitemap_url = sitemap_urls[0] if sitemap_urls else project.start_url
                sitemap_result = analyze_sitemap(sitemap_url)

                # Create a virtual page for robots.txt issues
                robots_page_url = project.start_url.rstrip("/") + "/robots.txt"
                robots_page = db.query(PageModel).filter(
                    PageModel.crawl_id == crawl_id,
                    PageModel.url == robots_page_url
                ).first()
                if not robots_page:
                    robots_page = PageModel(
                        crawl_id=crawl_id,
                        url=robots_page_url,
                        status_code=200 if robots_result.get("found") else 404,
                        depth=0,
                    )
                    db.add(robots_page)
                    db.flush()

                for iss in robots_result.get("issues", []):
                    try:
                        sev_enum = IssueSeverity(iss["severity"])
                    except ValueError:
                        sev_enum = IssueSeverity.INFO
                    db.add(Issue(
                        crawl_id=crawl_id,
                        page_id=robots_page.id,
                        severity=sev_enum,
                        issue_type=iss["type"],
                        description=iss["description"],
                        recommendation=iss.get("recommendation", ""),
                        category="technical",
                    ))
                    if sev_enum == IssueSeverity.CRITICAL:
                        n_critical += 1
                    elif sev_enum == IssueSeverity.WARNING:
                        n_warning += 1
                    else:
                        n_info += 1

                for iss in sitemap_result.get("issues", []):
                    try:
                        sev_enum = IssueSeverity(iss["severity"])
                    except ValueError:
                        sev_enum = IssueSeverity.INFO
                    db.add(Issue(
                        crawl_id=crawl_id,
                        page_id=robots_page.id,
                        severity=sev_enum,
                        issue_type=iss["type"],
                        description=iss["description"],
                        recommendation=iss.get("recommendation", ""),
                        category="technical",
                    ))
                    if sev_enum == IssueSeverity.CRITICAL:
                        n_critical += 1
                    elif sev_enum == IssueSeverity.WARNING:
                        n_warning += 1
                    else:
                        n_info += 1

                db.commit()
                logger.info("Crawl %d: robots/sitemap analysis done", crawl_id)
        except Exception as e:
            logger.error("robots/sitemap analysis failed for crawl %d: %s", crawl_id, e)
            db.rollback()

            # --- Post-crawl v0.7.0: Email Alerts ---
        try:
            from app.models import AlertConfig
            from app.notifications.email_sender import send_alert_email_sync
            import os
            alert_configs = db.query(AlertConfig).filter(
                AlertConfig.project_id == crawl.project_id,
                AlertConfig.enabled,
            ).all()
            for ac in alert_configs:
                should_send = False
                if ac.alert_on_crawl_complete:
                    should_send = True
                if ac.alert_on_critical and n_critical > 0:
                    should_send = True
                if not should_send:
                    continue
                # Get new critical issues for this crawl
                new_issues_list = []
                if ac.alert_on_new_issues or ac.alert_on_critical:
                    from app.models import Page as PageModel2
                    crit_issues = db.query(Issue, PageModel2.url).join(
                        PageModel2, Issue.page_id == PageModel2.id
                    ).filter(
                        Issue.crawl_id == crawl_id,
                        Issue.severity == IssueSeverity.CRITICAL,
                    ).limit(20).all()
                    new_issues_list = [
                        {"url": url, "type": iss.issue_type, "severity": "critical"}
                        for iss, url in crit_issues
                    ]
                crawl_stats = {
                    "crawl_id": crawl_id,
                    "crawled_urls": n_crawled,
                    "critical_issues": n_critical,
                    "warning_issues": n_warning,
                    "info_issues": n_info,
                }
                smtp_config = {
                    "host": ac.smtp_host,
                    "port": ac.smtp_port,
                    "user": ac.smtp_user,
                    "password": ac.smtp_password,
                }
                project_for_alert = db.query(Project).filter(Project.id == crawl.project_id).first()
                project_name = project_for_alert.name if project_for_alert else str(crawl.project_id)
                dashboard_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
                send_alert_email_sync(
                    to_email=ac.email,
                    project_name=project_name,
                    crawl_stats=crawl_stats,
                    new_issues=new_issues_list,
                    smtp_config=smtp_config,
                    dashboard_url=dashboard_url,
                )
        except Exception as e:
            logger.error("Email alert failed for crawl %d: %s", crawl_id, e)

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


# ═══════════════════════════════════════════════════════════════════════
# v0.8.0 Feature 2: Core Web Vitals measurement task
# ═══════════════════════════════════════════════════════════════════════

@celery_app.task(bind=True, name="tasks.measure_page_cwv", max_retries=2)
def measure_page_cwv(self, page_id: int, url: str):
    """Measure Core Web Vitals for a single page and persist to DB."""
    from app.database import SessionLocal
    from app.models import Page as PageModel
    from app.crawler.cwv_analyzer import measure_cwv_sync, score_cwv

    db = SessionLocal()
    try:
        metrics = measure_cwv_sync(url, timeout=30)
        if not metrics:
            return {"status": "no_metrics", "url": url}
        scores = score_cwv(metrics)
        page = db.query(PageModel).filter(PageModel.id == page_id).first()
        if page:
            page.lcp = metrics.get("lcp")
            page.cls = metrics.get("cls")
            page.fcp = metrics.get("fcp")
            page.ttfb = metrics.get("ttfb")
            page.tbt = metrics.get("tbt")
            page.dom_size = metrics.get("dom_size")
            page.cwv_score = scores.get("overall", "unknown")
            db.commit()
        return {"status": "ok", "url": url, "overall": scores.get("overall")}
    except Exception as e:
        logger.error("CWV measurement failed page_id=%d url=%s: %s", page_id, url, e)
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.measure_crawl_cwv", max_retries=1)
def measure_crawl_cwv(self, crawl_id: int, top_n: int = 50):
    """Queue CWV measurement for the top N pages of a crawl."""
    from app.database import SessionLocal
    from app.models import Page as PageModel

    db = SessionLocal()
    try:
        pages = (
            db.query(PageModel)
            .filter(
                PageModel.crawl_id == crawl_id,
                PageModel.status_code == 200,
            )
            .order_by(PageModel.internal_links_count.desc())
            .limit(top_n)
            .all()
        )
        for page in pages:
            measure_page_cwv.apply_async(
                args=[page.id, page.url],
                countdown=1,
                soft_time_limit=60,
            )
        return {"status": "queued", "count": len(pages)}
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# v0.8.0 Feature 4: GSC daily rank sync task
# ═══════════════════════════════════════════════════════════════════════

@celery_app.task(bind=True, name="tasks.sync_gsc_rankings", max_retries=2)
def sync_gsc_rankings(self):
    """Daily Celery Beat task: sync GSC keyword rankings for all linked projects."""
    from app.database import SessionLocal
    from app.models import GSCConnection, KeywordRanking
    from datetime import date

    db = SessionLocal()
    synced = 0
    errors = 0
    try:
        connections = db.query(GSCConnection).filter(
            GSCConnection.project_id.isnot(None),
            GSCConnection.site_url != "",
            GSCConnection.access_token.isnot(None),
        ).all()

        for conn in connections:
            try:
                from app.integrations.google_search_console import GSCClient
                client = GSCClient(
                    access_token=conn.access_token,
                    refresh_token=conn.refresh_token,
                    token_expiry=conn.token_expiry,
                )
                rows = client.get_keyword_rankings(conn.site_url, days=1)
                today = date.today()
                for row in rows:
                    kw = row.get("query")
                    row_date_str = row.get("date") or str(today)
                    try:
                        row_date = date.fromisoformat(row_date_str)
                    except (ValueError, TypeError):
                        row_date = today
                    existing = db.query(KeywordRanking).filter(
                        KeywordRanking.project_id == conn.project_id,
                        KeywordRanking.keyword == kw,
                        KeywordRanking.date == row_date,
                    ).first()
                    if existing:
                        existing.position = row.get("position")
                        existing.clicks = row.get("clicks", 0)
                        existing.impressions = row.get("impressions", 0)
                        existing.ctr = row.get("ctr")
                        existing.url = row.get("page")
                    else:
                        db.add(KeywordRanking(
                            project_id=conn.project_id,
                            keyword=kw,
                            date=row_date,
                            position=row.get("position"),
                            clicks=row.get("clicks", 0),
                            impressions=row.get("impressions", 0),
                            ctr=row.get("ctr"),
                            url=row.get("page"),
                        ))
                db.commit()
                synced += 1
                logger.info("GSC sync OK: project_id=%d site=%s rows=%d",
                            conn.project_id, conn.site_url, len(rows))
            except Exception as e:
                errors += 1
                logger.error("GSC sync failed for project_id=%d: %s", conn.project_id, e)
                db.rollback()

        return {"status": "done", "synced": synced, "errors": errors}
    finally:
        db.close()
