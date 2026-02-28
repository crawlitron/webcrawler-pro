
from datetime import datetime, timedelta
import logging
from celery import shared_task
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@shared_task(name="crawler.cleanup_old_crawls", bind=True, max_retries=3)
def cleanup_old_crawls(self, days: int = 90):
    """Remove crawl data older than `days` days to reclaim database space."""
    from app.database import SessionLocal
    from app.models import Crawl, CrawlStatus
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        old_crawls = db.query(Crawl).filter(
            Crawl.created_at < cutoff,
            Crawl.status.in_([
                CrawlStatus.COMPLETED,
                CrawlStatus.FAILED,
            ])
        ).all()
        count = len(old_crawls)
        for crawl in old_crawls:
            db.delete(crawl)
        db.commit()
        logger.info(f"cleanup_old_crawls: deleted {count} crawl(s) older than {days} days")
        return {"deleted": count, "cutoff": cutoff.isoformat()}
    except Exception as exc:
        db.rollback()
        logger.error(f"cleanup_old_crawls failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@shared_task(name="crawler.daily_health_check", bind=True, max_retries=2)
def daily_health_check(self):
    """Daily health-check: verify DB connectivity and summarize system state."""
    from app.database import engine, SessionLocal
    from app.models import Project, Crawl, CrawlStatus
    from sqlalchemy import text
    db: Session = SessionLocal()
    try:
        # Test DB connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        total_projects = db.query(Project).count()
        total_crawls = db.query(Crawl).count()
        running_crawls = db.query(Crawl).filter(
            Crawl.status == CrawlStatus.RUNNING
        ).count()
        failed_crawls_today = db.query(Crawl).filter(
            Crawl.status == CrawlStatus.FAILED,
            Crawl.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "db_status": "healthy",
            "total_projects": total_projects,
            "total_crawls": total_crawls,
            "running_crawls": running_crawls,
            "failed_crawls_last_24h": failed_crawls_today,
        }
        logger.info(f"daily_health_check: {report}")
        return report
    except Exception as exc:
        logger.error(f"daily_health_check failed: {exc}")
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
