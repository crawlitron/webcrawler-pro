from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Date, ForeignKey, Enum, JSON
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
    # v0.4.0 crawl config
    custom_user_agent = Column(String(512), nullable=True)
    crawl_delay = Column(Float, default=0.5)
    include_patterns = Column(Text, nullable=True)   # JSON array of regex strings
    exclude_patterns = Column(Text, nullable=True)   # JSON array of regex strings
    crawl_external_links = Column(Boolean, default=False)
    # v0.5.0
    crawl_schedule = Column(String(20), nullable=True)  # null | daily | weekly | monthly
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # v0.8.0 Feature 1: JavaScript Rendering
    use_js_rendering = Column(Boolean, default=False)
    js_wait_time = Column(Float, default=2.0)
    crawls = relationship("Crawl", back_populates="project", cascade="all, delete-orphan")

    ga4_token = relationship("GA4Token", back_populates="project", uselist=False)

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
    # v0.5.0
    performance_score = Column(Integer, nullable=True)  # 0-100
    # v0.8.0 Feature 2: Core Web Vitals
    lcp = Column(Float, nullable=True)
    cls = Column(Float, nullable=True)
    fcp = Column(Float, nullable=True)
    ttfb = Column(Float, nullable=True)
    tbt = Column(Float, nullable=True)
    dom_size = Column(Integer, nullable=True)
    cwv_score = Column(String(50), nullable=True)
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
    # v0.5.0
    category = Column(String(50), nullable=True)  # seo | accessibility | performance | etc.
    crawl = relationship("Crawl", back_populates="issues")
    page = relationship("Page", back_populates="issues")


# v0.7.0: Email Alert Configuration
class AlertConfig(Base):
    __tablename__ = 'alert_configs'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    email = Column(String(255), nullable=False)
    alert_on_critical = Column(Boolean, default=True)
    alert_on_new_issues = Column(Boolean, default=True)
    alert_on_crawl_complete = Column(Boolean, default=False)
    min_severity = Column(String(20), default='critical')
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_user = Column(String(255), nullable=True)
    smtp_password = Column(String(512), nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship('Project', backref='alert_configs')


# ═══════════════════════════════════════════════════════════════════════
# v0.8.0 Feature 3: Multi-User / Teams
# ═══════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(512), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    team_memberships = relationship("TeamMember", foreign_keys="TeamMember.user_id", back_populates="user", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    max_projects = Column(Integer, default=10)
    max_crawl_urls = Column(Integer, default=10000)
    owner = relationship("User", foreign_keys=[Column(Integer)])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    team_projects = relationship("TeamProject", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="viewer")  # owner/admin/editor/viewer
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    team = relationship("Team", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="team_memberships")


class TeamProject(Base):
    __tablename__ = "team_projects"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    team = relationship("Team", back_populates="team_projects")
    project = relationship("Project")


# ═══════════════════════════════════════════════════════════════════════
# v0.8.0 Feature 4: Google Search Console + Rank Tracking
# ═══════════════════════════════════════════════════════════════════════

class GSCConnection(Base):
    __tablename__ = "gsc_connections"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    site_url = Column(String(2048), nullable=False)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
    project = relationship("Project")


class KeywordRanking(Base):
    __tablename__ = "keyword_rankings"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    keyword = Column(String(512), nullable=False)
    date = Column(Date, nullable=False)
    position = Column(Float, nullable=True)
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, nullable=True)
    url = Column(String(2048), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project")


# ═══════════════════════════════════════════════════════════════════════
# v0.9.0 Feature: Google Analytics 4 Integration
# ═══════════════════════════════════════════════════════════════════════

from sqlalchemy import Date, Index


class GA4Token(Base):
    """Google Analytics 4 OAuth tokens and connection info."""
    __tablename__ = 'ga4_tokens'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), unique=True, nullable=False)
    access_token = Column(String(512), nullable=False)
    refresh_token = Column(String(512), nullable=False)
    property_id = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship('Project', back_populates='ga4_token')


class GA4Metric(Base):
    """Google Analytics 4 metrics data."""
    __tablename__ = 'ga4_metrics'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    date = Column(Date, nullable=False)
    page_path = Column(String(2048), nullable=True)
    sessions = Column(Integer, default=0)
    pageviews = Column(Integer, default=0)
    bounce_rate = Column(Float, default=0.0)
    avg_duration = Column(Float, default=0.0)
    device_category = Column(String(50), nullable=True)
    source_medium = Column(String(255), nullable=True)
    conversions = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_ga4_metrics_project_date', 'project_id', 'date'),
        Index('ix_ga4_metrics_page', 'project_id', 'page_path'),
    )
    
    project = relationship('Project')
