
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db
from ..models import Project, Crawl
from ..schemas import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _to_response(project: Project, db: Session) -> ProjectResponse:
    last = db.query(Crawl).filter(Crawl.project_id == project.id).order_by(desc(Crawl.created_at)).first()
    return ProjectResponse(
        id=project.id, name=project.name, start_url=project.start_url,
        max_urls=project.max_urls, created_at=project.created_at,
        updated_at=project.updated_at,
        last_crawl_status=last.status.value if last else None,
        last_crawl_id=last.id if last else None,
    )


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    url = body.start_url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "start_url must begin with http:// or https://")
    proj = Project(name=body.name, start_url=url, max_urls=body.max_urls)
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


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    db.delete(p)
    db.commit()
