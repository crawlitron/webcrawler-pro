import re
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Team, TeamMember, TeamProject, Project, User
from .auth import get_db, require_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/teams", tags=["teams"])

ROLES = ("owner", "admin", "editor", "viewer")
ROLE_RANK = {r: i for i, r in enumerate(ROLES)}


class TeamCreate(BaseModel):
    name: str


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    max_projects: Optional[int] = None
    max_crawl_urls: Optional[int] = None


class MemberRoleUpdate(BaseModel):
    role: str


class InviteRequest(BaseModel):
    email: str
    role: str = "viewer"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _make_slug_unique(db: Session, base: str) -> str:
    slug = base
    n = 1
    while db.query(Team).filter(Team.slug == slug).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _require_role(db: Session, team_id: int, user_id: int, min_role: str) -> TeamMember:
    m = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first()
    if not m:
        raise HTTPException(403, "Not a member of this team")
    if ROLE_RANK.get(m.role, 99) > ROLE_RANK.get(min_role, 99):
        raise HTTPException(403, f"Requires role: {min_role}")
    return m


def _team_out(team: Team, db: Session, current_user_id: int) -> dict:
    member = db.query(TeamMember).filter(TeamMember.team_id == team.id, TeamMember.user_id == current_user_id).first()
    return {
        "id": team.id,
        "name": team.name,
        "slug": team.slug,
        "owner_id": team.owner_id,
        "created_at": team.created_at,
        "max_projects": team.max_projects,
        "max_crawl_urls": team.max_crawl_urls,
        "member_count": db.query(TeamMember).filter(TeamMember.team_id == team.id).count(),
        "my_role": member.role if member else None,
    }


@router.get("")
def list_teams(current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    memberships = db.query(TeamMember).filter(TeamMember.user_id == current_user.id).all()
    teams = [db.query(Team).filter(Team.id == m.team_id).first() for m in memberships]
    return [_team_out(t, db, current_user.id) for t in teams if t]


@router.post("", status_code=201)
def create_team(data: TeamCreate, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    slug = _make_slug_unique(db, _slug(data.name))
    team = Team(name=data.name, slug=slug, owner_id=current_user.id)
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=current_user.id, role="owner"))
    db.commit()
    db.refresh(team)
    return _team_out(team, db, current_user.id)


@router.get("/{team_id}")
def get_team(team_id: int, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(404, "Team not found")
    _require_role(db, team_id, current_user.id, "viewer")
    return _team_out(team, db, current_user.id)


@router.put("/{team_id}")
def update_team(team_id: int, data: TeamUpdate, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(404, "Team not found")
    _require_role(db, team_id, current_user.id, "admin")
    if data.name is not None:
        team.name = data.name
    if data.max_projects is not None:
        team.max_projects = data.max_projects
    if data.max_crawl_urls is not None:
        team.max_crawl_urls = data.max_crawl_urls
    db.commit()
    return _team_out(team, db, current_user.id)


@router.delete("/{team_id}")
def delete_team(team_id: int, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(404, "Team not found")
    if team.owner_id != current_user.id:
        raise HTTPException(403, "Only the owner can delete a team")
    db.delete(team)
    db.commit()
    return {"message": "Team deleted"}


@router.get("/{team_id}/members")
def list_members(team_id: int, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    _require_role(db, team_id, current_user.id, "viewer")
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    result = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        result.append({"id": m.id, "user_id": m.user_id, "email": u.email if u else None,
                       "full_name": u.full_name if u else None, "role": m.role, "joined_at": m.joined_at})
    return result


@router.post("/{team_id}/invite", status_code=201)
def invite_member(team_id: int, data: InviteRequest, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    _require_role(db, team_id, current_user.id, "admin")
    if data.role not in ROLES:
        raise HTTPException(400, f"Invalid role. Choose from: {ROLES}")
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(404, "User not found — they must register first")
    existing = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user.id).first()
    if existing:
        raise HTTPException(400, "User already a member")
    db.add(TeamMember(team_id=team_id, user_id=user.id, role=data.role, invited_by=current_user.id))
    db.commit()
    return {"message": f"User {data.email} added with role {data.role}"}


@router.put("/{team_id}/members/{user_id}")
def update_member_role(team_id: int, user_id: int, data: MemberRoleUpdate,
                       current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    _require_role(db, team_id, current_user.id, "admin")
    if data.role not in ROLES:
        raise HTTPException(400, f"Invalid role")
    m = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first()
    if not m:
        raise HTTPException(404, "Member not found")
    if m.role == "owner":
        raise HTTPException(403, "Cannot change the owner's role")
    m.role = data.role
    db.commit()
    return {"message": "Role updated"}


@router.delete("/{team_id}/members/{user_id}")
def remove_member(team_id: int, user_id: int, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    _require_role(db, team_id, current_user.id, "admin")
    m = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first()
    if not m:
        raise HTTPException(404, "Member not found")
    if m.role == "owner":
        raise HTTPException(403, "Cannot remove the owner")
    db.delete(m)
    db.commit()
    return {"message": "Member removed"}


@router.get("/{team_id}/projects")
def list_team_projects(team_id: int, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    _require_role(db, team_id, current_user.id, "viewer")
    links = db.query(TeamProject).filter(TeamProject.team_id == team_id).all()
    projects = [db.query(Project).filter(Project.id == lk.project_id).first() for lk in links]
    return [{"id": p.id, "name": p.name, "start_url": p.start_url} for p in projects if p]


@router.post("/{team_id}/projects/{project_id}", status_code=201)
def add_team_project(team_id: int, project_id: int, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    _require_role(db, team_id, current_user.id, "editor")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    existing = db.query(TeamProject).filter(TeamProject.team_id == team_id, TeamProject.project_id == project_id).first()
    if existing:
        raise HTTPException(400, "Project already linked to team")
    db.add(TeamProject(team_id=team_id, project_id=project_id))
    db.commit()
    return {"message": "Project linked to team"}
