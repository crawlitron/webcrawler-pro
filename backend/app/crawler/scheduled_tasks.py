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
        logger.info("cleanup_old_crawls: deleted %d crawl(s) older than %d days", count, days)
        return {"deleted": count, "cutoff": cutoff.isoformat()}
    except Exception as exc:
        db.rollback()
        logger.error("cleanup_old_crawls failed: %s", exc)
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
        logger.info("daily_health_check: %s", report)
        return report
    except Exception as exc:
        logger.error("daily_health_check failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


@shared_task(name="crawler.run_scheduled_crawls", bind=True, max_retries=1)
def run_scheduled_crawls(self):
    """v0.5.0: Periodic task — check all projects with crawl_schedule and trigger crawls when due.

    Schedule thresholds:
      daily   — crawl if last completed crawl was more than 23 hours ago
      weekly  — crawl if last completed crawl was more than 6 days 23 hours ago
      monthly — crawl if last completed crawl was more than 29 days ago
    """
    from app.database import SessionLocal
    from app.models import Project, Crawl, CrawlStatus
    from app.crawler.tasks import run_crawl
    import json

    db: Session = SessionLocal()
    triggered = []
    skipped = []

    SCHEDULE_THRESHOLDS = {
        "daily": timedelta(hours=23),
        "weekly": timedelta(days=6, hours=23),
        "monthly": timedelta(days=29),
    }

    try:
        projects = db.query(Project).filter(
            Project.crawl_schedule.isnot(None),
            Project.crawl_schedule != "",
        ).all()

        logger.info("run_scheduled_crawls: checking %d scheduled project(s)", len(projects))

        for project in projects:
            schedule = (project.crawl_schedule or "").strip().lower()
            if schedule not in SCHEDULE_THRESHOLDS:
                logger.warning(
                    "Project %d has unknown crawl_schedule value: %s — skipping",
                    project.id, schedule
                )
                continue

            threshold = SCHEDULE_THRESHOLDS[schedule]

            # Find most recent completed crawl
            last_crawl = (
                db.query(Crawl)
                .filter(
                    Crawl.project_id == project.id,
                    Crawl.status == CrawlStatus.COMPLETED,
                )
                .order_by(Crawl.completed_at.desc())
                .first()
            )

            # Also check for any currently running crawl to avoid duplicates
            running_crawl = (
                db.query(Crawl)
                .filter(
                    Crawl.project_id == project.id,
                    Crawl.status == CrawlStatus.RUNNING,
                )
                .first()
            )

            if running_crawl:
                logger.info(
                    "Project %d (%s): crawl already running (crawl_id=%d) — skipping",
                    project.id, project.name, running_crawl.id
                )
                skipped.append({"project_id": project.id, "reason": "already_running"})
                continue

            now = datetime.utcnow()
            crawl_due = False

            if last_crawl is None:
                # Never crawled — trigger immediately
                crawl_due = True
                logger.info(
                    "Project %d (%s): no previous crawl found — triggering first scheduled crawl",
                    project.id, project.name
                )
            else:
                last_ts = last_crawl.completed_at or last_crawl.created_at
                age = now - last_ts
                if age >= threshold:
                    crawl_due = True
                    logger.info(
                        "Project %d (%s): last crawl %s ago (threshold %s) — triggering",
                        project.id, project.name,
                        str(age).split(".")[0], str(threshold)
                    )
                else:
                    logger.info(
                        "Project %d (%s): last crawl %s ago — not yet due (threshold %s)",
                        project.id, project.name,
                        str(age).split(".")[0], str(threshold)
                    )
                    skipped.append({
                        "project_id": project.id,
                        "reason": "not_due_yet",
                        "last_crawl_age_hours": round(age.total_seconds() / 3600, 1),
                    })

            if not crawl_due:
                continue

            # Create a new Crawl record
            new_crawl = Crawl(
                project_id=project.id,
                status=CrawlStatus.PENDING,
                total_urls=0,
                crawled_urls=0,
                failed_urls=0,
                critical_issues=0,
                warning_issues=0,
                info_issues=0,
            )
            db.add(new_crawl)
            db.commit()
            db.refresh(new_crawl)

            # Resolve include/exclude patterns
            include_patterns = []
            exclude_patterns = []
            if project.include_patterns:
                try:
                    inc = project.include_patterns
                    include_patterns = json.loads(inc) if isinstance(inc, str) else (inc or [])
                except (ValueError, TypeError):
                    include_patterns = []
            if project.exclude_patterns:
                try:
                    exc = project.exclude_patterns
                    exclude_patterns = json.loads(exc) if isinstance(exc, str) else (exc or [])
                except (ValueError, TypeError):
                    exclude_patterns = []

            # Dispatch Celery task
            run_crawl.delay(
                crawl_id=new_crawl.id,
                start_url=project.start_url,
                max_urls=project.max_urls or 500,
                custom_user_agent=project.custom_user_agent,
                crawl_delay=project.crawl_delay or 0.5,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                crawl_external_links=project.crawl_external_links or False,
            )

            logger.info(
                "Scheduled crawl triggered: project_id=%d crawl_id=%d schedule=%s",
                project.id, new_crawl.id, schedule
            )
            triggered.append({
                "project_id": project.id,
                "crawl_id": new_crawl.id,
                "schedule": schedule,
            })

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "triggered": triggered,
            "skipped": skipped,
            "total_checked": len(projects),
        }

    except Exception as exc:
        logger.error("run_scheduled_crawls failed: %s", exc)
        db.rollback()
        raise self.retry(exc=exc, countdown=120)
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# v0.9.0 Feature: Google Analytics 4 Sync Tasks
# ═══════════════════════════════════════════════════════════════════════

@shared_task(name="ga4.sync_project", bind=True, max_retries=3)
def sync_ga4_data(self, project_id: int):
    """Daily GA4 data sync for connected projects."""
    from app.database import SessionLocal
    from app.integrations.google_analytics import GA4Integration
    import asyncio

    db: Session = SessionLocal()
    try:
        ga4 = GA4Integration(db)
        asyncio.run(ga4.sync_to_db(project_id))
        logger.info("GA4 sync completed for project %s", project_id)
        return {"project_id": project_id, "status": "success"}
    except Exception as exc:
        logger.error("GA4 sync failed for project %s: %s", project_id, exc)
        db.rollback()
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()


@shared_task(name="ga4.sync_all_projects", bind=True, max_retries=1)
def sync_all_ga4_projects(self):
    """Sync all projects with GA4 connections."""
    from app.database import SessionLocal
    from app.models import GA4Token

    db: Session = SessionLocal()
    try:
        tokens = db.query(GA4Token).all()
        count = len(tokens)

        for token in tokens:
            sync_ga4_data.delay(token.project_id)

        logger.info("Triggered GA4 sync for %s projects", count)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "projects_triggered": count,
        }
    except Exception as exc:
        logger.error("Failed to trigger GA4 syncs: %s", exc)
        raise self.retry(exc=exc, countdown=120)
    finally:
        db.close()
