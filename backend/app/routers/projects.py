import json
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db
from ..models import Project, Crawl
from ..schemas import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _to_response(project: Project, db: Session) -> ProjectResponse:
    last = db.query(Crawl).filter(
        Crawl.project_id == project.id).order_by(desc(Crawl.created_at)).first()
    # Deserialize JSON pattern fields
    include_pats = None
    exclude_pats = None
    try:
        if project.include_patterns:
            include_pats = json.loads(project.include_patterns)
    except (ValueError, TypeError):
        include_pats = None
    try:
        if project.exclude_patterns:
            exclude_pats = json.loads(project.exclude_patterns)
    except (ValueError, TypeError):
        exclude_pats = None
    return ProjectResponse(
        id=project.id,
        name=project.name,
        start_url=project.start_url,
        max_urls=project.max_urls,
        custom_user_agent=project.custom_user_agent,
        crawl_delay=project.crawl_delay if project.crawl_delay is not None else 0.5,
        include_patterns=include_pats,
        exclude_patterns=exclude_pats,
        crawl_external_links=project.crawl_external_links or False,
        created_at=project.created_at,
        updated_at=project.updated_at,
        last_crawl_status=last.status.value if last else None,
        last_crawl_id=last.id if last else None,
    )


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    url = body.start_url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "start_url must begin with http:// or https://")
    proj = Project(
        name=body.name,
        start_url=url,
        max_urls=body.max_urls,
        custom_user_agent=body.custom_user_agent,
        crawl_delay=body.crawl_delay,
        include_patterns=json.dumps(body.include_patterns) if body.include_patterns else None,
        exclude_patterns=json.dumps(body.exclude_patterns) if body.exclude_patterns else None,
        crawl_external_links=body.crawl_external_links,
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return _to_response(proj, db)


@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return [_to_response(p, db) for p in db.query(Project).order_by(desc(Project.created_at)).all()]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    return _to_response(p, db)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, body: ProjectUpdate, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    if body.name is not None:
        p.name = body.name
    if body.start_url is not None:
        url = body.start_url.strip()
        if not url.startswith(("http://", "https://")):
            raise HTTPException(400, "start_url must begin with http:// or https://")
        p.start_url = url
    if body.max_urls is not None:
        p.max_urls = body.max_urls
    if body.custom_user_agent is not None:
        p.custom_user_agent = body.custom_user_agent
    if body.crawl_delay is not None:
        p.crawl_delay = body.crawl_delay
    if body.include_patterns is not None:
        p.include_patterns = json.dumps(body.include_patterns) if body.include_patterns else None
    if body.exclude_patterns is not None:
        p.exclude_patterns = json.dumps(body.exclude_patterns) if body.exclude_patterns else None
    if body.crawl_external_links is not None:
        p.crawl_external_links = body.crawl_external_links
    db.commit()
    db.refresh(p)
    return _to_response(p, db)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    db.delete(p)
    db.commit()
