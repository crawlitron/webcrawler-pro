from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from .models import CrawlStatus, IssueSeverity


class ProjectCreate(BaseModel):
    name: str
    start_url: str
    max_urls: int = 500
    custom_user_agent: Optional[str] = None
    crawl_delay: float = 0.5
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    crawl_external_links: bool = False
    crawl_schedule: Optional[str] = None  # v0.5.0: null | daily | weekly | monthly


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    start_url: Optional[str] = None
    max_urls: Optional[int] = None
    custom_user_agent: Optional[str] = None
    crawl_delay: Optional[float] = None
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    crawl_external_links: Optional[bool] = None
    crawl_schedule: Optional[str] = None  # v0.5.0


class ProjectResponse(BaseModel):
    id: int
    name: str
    start_url: str
    max_urls: int
    custom_user_agent: Optional[str] = None
    crawl_delay: float = 0.5
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    crawl_external_links: bool = False
    crawl_schedule: Optional[str] = None  # v0.5.0
    created_at: datetime
    updated_at: datetime
    last_crawl_status: Optional[str] = None
    last_crawl_id: Optional[int] = None
    model_config = {"from_attributes": True}


class CrawlResponse(BaseModel):
    id: int
    project_id: int
    status: CrawlStatus
    celery_task_id: Optional[str] = None
    total_urls: int
    crawled_urls: int
    failed_urls: int
    critical_issues: int
    warning_issues: int
    info_issues: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    error_message: Optional[str] = None
    progress_percent: Optional[float] = None
    model_config = {"from_attributes": True}


class PageResponse(BaseModel):
    id: int
    crawl_id: int
    url: str
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    response_time: Optional[float] = None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1: Optional[str] = None
    h2_count: int = 0
    canonical_url: Optional[str] = None
    internal_links_count: int = 0
    external_links_count: int = 0
    images_without_alt: int = 0
    word_count: int = 0
    is_indexable: bool = True
    redirect_url: Optional[str] = None
    depth: int = 0
    crawled_at: datetime
    issue_count: int = 0
    extra_data: Optional[dict] = None
    performance_score: Optional[int] = None  # v0.5.0
    model_config = {"from_attributes": True}


class PageListResponse(BaseModel):
    items: List[PageResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class IssueResponse(BaseModel):
    id: int
    crawl_id: int
    page_id: int
    page_url: Optional[str] = None
    severity: IssueSeverity
    issue_type: str
    description: str
    recommendation: Optional[str] = None
    category: Optional[str] = None  # v0.5.0
    model_config = {"from_attributes": True}


class IssueListResponse(BaseModel):
    items: List[IssueResponse]
    total: int
    critical: int
    warning: int
    info: int


# Setup Wizard Schemas
from typing import Dict, Optional as Opt

class SetupStatus(BaseModel):
    completed: bool
    steps_done: list

class AdminSetup(BaseModel):
    email: str
    password: str
    full_name: Opt[str] = None

class SetupCompleteRequest(BaseModel):
    admin: AdminSetup
    settings: Dict[str, str] = {}
