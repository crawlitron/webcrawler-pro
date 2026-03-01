import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .database import engine, Base
from .routers import projects, crawls, pages, analytics
from .routers import auth, teams, integrations
from .routers import setup
from .routers import mobile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations():
    """Idempotent schema migrations — add new columns/tables if they do not exist."""
    migrations = [
        "CREATE TABLE IF NOT EXISTS app_settings (key VARCHAR(255) PRIMARY KEY, value TEXT, is_sensitive BOOLEAN DEFAULT FALSE, updated_at TIMESTAMP)",
        # v0.4.0: extended crawl configuration
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS custom_user_agent VARCHAR(512)",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS crawl_delay FLOAT DEFAULT 0.5",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS include_patterns TEXT",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS exclude_patterns TEXT",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS crawl_external_links BOOLEAN DEFAULT FALSE",
        "ALTER TABLE pages ADD COLUMN IF NOT EXISTS extra_data JSON",
        # v0.5.0
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS crawl_schedule VARCHAR(20)",
        "ALTER TABLE pages ADD COLUMN IF NOT EXISTS performance_score INTEGER",
        "ALTER TABLE issues ADD COLUMN IF NOT EXISTS category VARCHAR(50)",
        # v0.8.0 Feature 1: JS Rendering
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS use_js_rendering BOOLEAN DEFAULT FALSE",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS js_wait_time FLOAT DEFAULT 2.0",
        # v0.8.0 Feature 2: Core Web Vitals
        "ALTER TABLE pages ADD COLUMN IF NOT EXISTS lcp FLOAT",
        "ALTER TABLE pages ADD COLUMN IF NOT EXISTS cls FLOAT",
        "ALTER TABLE pages ADD COLUMN IF NOT EXISTS fcp FLOAT",
        "ALTER TABLE pages ADD COLUMN IF NOT EXISTS ttfb FLOAT",
        "ALTER TABLE pages ADD COLUMN IF NOT EXISTS tbt FLOAT",
        "ALTER TABLE pages ADD COLUMN IF NOT EXISTS dom_size INTEGER",
        "ALTER TABLE pages ADD COLUMN IF NOT EXISTS cwv_score VARCHAR(50)",
        # v0.8.0 Feature 3: Users / Teams (CREATE TABLE IF NOT EXISTS)
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(512) NOT NULL,
            full_name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            last_login TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS teams (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) UNIQUE NOT NULL,
            owner_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT NOW(),
            max_projects INTEGER DEFAULT 10,
            max_crawl_urls INTEGER DEFAULT 10000
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS team_members (
            id SERIAL PRIMARY KEY,
            team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            role VARCHAR(20) DEFAULT 'viewer',
            invited_by INTEGER REFERENCES users(id),
            joined_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS team_projects (
            id SERIAL PRIMARY KEY,
            team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE
        )
        """,
        # v0.8.0 Feature 4: GSC + Rank Tracking
        """
        CREATE TABLE IF NOT EXISTS gsc_connections (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
            site_url VARCHAR(2048) NOT NULL DEFAULT '',
            access_token TEXT,
            refresh_token TEXT,
            token_expiry TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS keyword_rankings (
            id SERIAL PRIMARY KEY,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            keyword VARCHAR(512) NOT NULL,
            date DATE NOT NULL,
            position FLOAT,
            clicks INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            ctr FLOAT,
            url VARCHAR(2048),
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        # v0.9.0: Google Analytics 4 Integration
        """
        CREATE TABLE IF NOT EXISTS ga4_tokens (
            id SERIAL PRIMARY KEY,
            project_id INTEGER UNIQUE NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            access_token VARCHAR(512) NOT NULL,
            refresh_token VARCHAR(512) NOT NULL,
            property_id VARCHAR(255) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ga4_metrics (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            page_path VARCHAR(2048),
            sessions INTEGER DEFAULT 0,
            pageviews INTEGER DEFAULT 0,
            bounce_rate FLOAT DEFAULT 0.0,
            avg_duration FLOAT DEFAULT 0.0,
            device_category VARCHAR(50),
            source_medium VARCHAR(255),
            conversions INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ga4_metrics_project_date 
        ON ga4_metrics (project_id, date)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ga4_metrics_page 
        ON ga4_metrics (project_id, page_path)
        """,
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception as e:
                logger.warning("Migration skipped (%s): %s", str(sql).strip()[:60], e)
                conn.rollback()
    logger.info("Database migrations applied (v0.8.0)")


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
    version="0.8.0",
    lifespan=lifespan,
)


def _get_cors_origins() -> list:
    """Build CORS origins list from environment.
    Supports wildcard '*' for development or Nginx-proxied deployments.
    """
    cors_env = os.getenv("CORS_ORIGINS", "")
    if cors_env == "*":
        return ["*"]
    origins = [
        "http://localhost:3000",
        "http://localhost:44544",
        "http://frontend:3000",
    ]
    if cors_env:
        for o in cors_env.split(","):
            o = o.strip()
            if o and o not in origins:
                origins.append(o)
    frontend_url = os.getenv("FRONTEND_URL", "")
    if frontend_url and frontend_url not in origins:
        origins.append(frontend_url)
    return origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
)

# Core routers
app.include_router(projects.router)
app.include_router(crawls.router)
app.include_router(pages.router)
app.include_router(analytics.router)

# v0.8.0 routers
app.include_router(setup.router)
app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(integrations.router)
app.include_router(mobile.router)

# Optional routers (loaded if module exists)
try:
    from .routers import seo_tools
    app.include_router(seo_tools.router)
except ImportError:
    pass
try:
    from .routers import compare
    app.include_router(compare.router)
except ImportError:
    pass
try:
    from .routers import reports
    app.include_router(reports.router)
except ImportError:
    pass
try:
    from .routers import alerts
    app.include_router(alerts.router)
except ImportError:
    pass


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "db": "connected", "version": "0.8.0"}
    except Exception as e:
        return {"status": "unhealthy", "db": str(e)}


@app.get("/")
def root():
    return {"name": "WebCrawler Pro", "version": "0.8.0", "docs": "/docs"}


@app.on_event("startup")
async def seed_test_account():
    """Create default test account wcp@wcp.local / wcp on first start."""
    try:
        from .routers.auth import hash_password
        from .models import User
        db = next(iter([SessionLocal()]))
        try:
            exists = db.query(User).filter(User.email == "wcp@wcp.local").first()
            if not exists:
                test_user = User(
                    email="wcp@wcp.local",
                    hashed_password=hash_password("wcp"),
                    full_name="Test User (WCP)",
                    is_admin=False,
                    is_active=True,
                )
                db.add(test_user)
                db.commit()
                logger.info("✅ Test account created: wcp@wcp.local / wcp")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not seed test account: {e}")
