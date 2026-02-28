
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


def create_tables(retries=10, delay=3):
    for i in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
            return
        except Exception as e:
            logger.warning(f"DB not ready (attempt {i + 1}/{retries}): {e}")
            time.sleep(delay)
    raise RuntimeError("Could not connect to database after multiple retries")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="WebCrawler Pro API",
    description="SEO Crawler API — Screaming Frog alternative",
    version="2.0.0",
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
        return {"status": "healthy", "db": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "db": str(e)}


@app.get("/")
def root():
    return {"name": "WebCrawler Pro", "version": "1.0.0", "docs": "/docs"}
