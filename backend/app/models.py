
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from .database import Base


class CrawlStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IssueSeverity(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    start_url = Column(String(2048), nullable=False)
    max_urls = Column(Integer, default=500)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    crawls = relationship("Crawl", back_populates="project", cascade="all, delete-orphan")


class Crawl(Base):
    __tablename__ = "crawls"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    status = Column(Enum(CrawlStatus), default=CrawlStatus.PENDING)
    celery_task_id = Column(String(255), nullable=True)
    total_urls = Column(Integer, default=0)
    crawled_urls = Column(Integer, default=0)
    failed_urls = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    warning_issues = Column(Integer, default=0)
    info_issues = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    project = relationship("Project", back_populates="crawls")
    pages = relationship("Page", back_populates="crawl", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="crawl", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"
    id = Column(Integer, primary_key=True, index=True)
    crawl_id = Column(Integer, ForeignKey("crawls.id"), nullable=False)
    url = Column(String(2048), nullable=False)
    status_code = Column(Integer, nullable=True)
    content_type = Column(String(255), nullable=True)
    response_time = Column(Float, nullable=True)
    title = Column(Text, nullable=True)
    meta_description = Column(Text, nullable=True)
    h1 = Column(Text, nullable=True)
    h2_count = Column(Integer, default=0)
    canonical_url = Column(String(2048), nullable=True)
    internal_links_count = Column(Integer, default=0)
    external_links_count = Column(Integer, default=0)
    images_without_alt = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    is_indexable = Column(Boolean, default=True)
    redirect_url = Column(String(2048), nullable=True)
    depth = Column(Integer, default=0)
    crawled_at = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(JSON, nullable=True)
    crawl = relationship("Crawl", back_populates="pages")
    issues = relationship("Issue", back_populates="page", cascade="all, delete-orphan")


class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True, index=True)
    crawl_id = Column(Integer, ForeignKey("crawls.id"), nullable=False)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    severity = Column(Enum(IssueSeverity), nullable=False)
    issue_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)
    crawl = relationship("Crawl", back_populates="issues")
    page = relationship("Page", back_populates="issues")
