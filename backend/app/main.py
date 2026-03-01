import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .database import engine, Base
from .routers import projects, crawls, pages, analytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations():
    """Idempotent schema migrations — add new columns if they do not exist."""
    migrations = [
        # v0.4.0: extended crawl configuration
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS custom_user_agent VARCHAR(512)",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS crawl_delay FLOAT DEFAULT 0.5",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS include_patterns TEXT",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS exclude_patterns TEXT",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS crawl_external_links BOOLEAN DEFAULT FALSE",
        # v0.4.0: extra_data JSON column for pages (stores images, redirect chains, etc.)
        "ALTER TABLE pages ADD COLUMN IF NOT EXISTS extra_data JSON",
        # v0.5.0: scheduled crawls
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS crawl_schedule VARCHAR(20)",
        # v0.5.0: performance scoring
        "ALTER TABLE pages ADD COLUMN IF NOT EXISTS performance_score INTEGER",
        # v0.5.0: issue categorization (seo | accessibility | performance)
        "ALTER TABLE issues ADD COLUMN IF NOT EXISTS category VARCHAR(50)",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception as e:
                logger.warning("Migration skipped (%s): %s", sql[:60], e)
                conn.rollback()
    logger.info("Database migrations applied (v0.5.0)")


def create_tables(retries=10, delay=3):
    for i in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified successfully")
            run_migrations()
            return
        except Exception as e:
            logger.warning("DB not ready (attempt %d/%d): %s", i + 1, retries, e)
            time.sleep(delay)
    raise RuntimeError("Could not connect to database after multiple retries")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="WebCrawler Pro API",
    description="SEO Crawler API — Screaming Frog alternative",
    version="0.5.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend:3000",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
)

app.include_router(projects.router)
app.include_router(crawls.router)
app.include_router(pages.router)
app.include_router(analytics.router)


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "db": "connected", "version": "0.5.0"}
    except Exception as e:
        return {"status": "unhealthy", "db": str(e)}


@app.get("/")
def root():
    return {"name": "WebCrawler Pro", "version": "0.5.0", "docs": "/docs"}
