import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "webcrawler",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.crawler.tasks"],
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
    # v0.8.0: Beat schedule for recurring tasks
    beat_schedule={
        # GSC rank tracking: runs daily at 03:00 UTC
        "sync-gsc-rankings-daily": {
            "task": "tasks.sync_gsc_rankings",
            "schedule": crontab(hour=3, minute=0),
        },
        # Scheduled crawls: check every hour (existing logic in scheduled_tasks.py)
        "run-scheduled-crawls": {
            "task": "tasks.run_scheduled_crawls",
            "schedule": crontab(minute=0),
        },
    },
)

if __name__ == "__main__":
    celery_app.start()
