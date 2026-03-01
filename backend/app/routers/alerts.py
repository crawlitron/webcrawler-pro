import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..models import AlertConfig, Project

router = APIRouter(prefix="/api/projects", tags=["alerts"])


class AlertConfigCreate(BaseModel):
    email: str
    alert_on_critical: bool = True
    alert_on_new_issues: bool = True
    alert_on_crawl_complete: bool = False
    min_severity: str = "critical"
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    enabled: bool = True


class AlertConfigUpdate(BaseModel):
    email: Optional[str] = None
    alert_on_critical: Optional[bool] = None
    alert_on_new_issues: Optional[bool] = None
    alert_on_crawl_complete: Optional[bool] = None
    min_severity: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    enabled: Optional[bool] = None


def _alert_to_dict(alert: AlertConfig) -> dict:
    return {
        "id": alert.id,
        "project_id": alert.project_id,
        "email": alert.email,
        "alert_on_critical": alert.alert_on_critical,
        "alert_on_new_issues": alert.alert_on_new_issues,
        "alert_on_crawl_complete": alert.alert_on_crawl_complete,
        "min_severity": alert.min_severity,
        "smtp_host": alert.smtp_host,
        "smtp_port": alert.smtp_port,
        "smtp_user": alert.smtp_user,
        "smtp_password": "***" if alert.smtp_password else None,
        "enabled": alert.enabled,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


@router.get("/{project_id}/alerts")
def get_alerts(project_id: int, db: Session = Depends(get_db)):
    """Get all alert configurations for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    alerts = db.query(AlertConfig).filter(AlertConfig.project_id == project_id).all()
    return [_alert_to_dict(a) for a in alerts]


@router.post("/{project_id}/alerts")
def create_alert(project_id: int, data: AlertConfigCreate, db: Session = Depends(get_db)):
    """Create a new alert configuration."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    alert = AlertConfig(
        project_id=project_id,
        email=data.email,
        alert_on_critical=data.alert_on_critical,
        alert_on_new_issues=data.alert_on_new_issues,
        alert_on_crawl_complete=data.alert_on_crawl_complete,
        min_severity=data.min_severity,
        smtp_host=data.smtp_host,
        smtp_port=data.smtp_port,
        smtp_user=data.smtp_user,
        smtp_password=data.smtp_password,
        enabled=data.enabled,
        created_at=datetime.utcnow(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _alert_to_dict(alert)


@router.put("/{project_id}/alerts/{alert_id}")
def update_alert(project_id: int, alert_id: int, data: AlertConfigUpdate, db: Session = Depends(get_db)):
    """Update an alert configuration."""
    alert = db.query(AlertConfig).filter(
        AlertConfig.id == alert_id,
        AlertConfig.project_id == project_id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert config not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(alert, key, val)
    db.commit()
    db.refresh(alert)
    return _alert_to_dict(alert)


@router.delete("/{project_id}/alerts/{alert_id}")
def delete_alert(project_id: int, alert_id: int, db: Session = Depends(get_db)):
    """Delete an alert configuration."""
    alert = db.query(AlertConfig).filter(
        AlertConfig.id == alert_id,
        AlertConfig.project_id == project_id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert config not found")
    db.delete(alert)
    db.commit()
    return {"message": "Alert deleted"}


@router.post("/{project_id}/alerts/test")
async def test_alert(project_id: int, db: Session = Depends(get_db)):
    """Send a test email using the project's first active alert config."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    alert = db.query(AlertConfig).filter(
        AlertConfig.project_id == project_id,
        AlertConfig.enabled,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="No enabled alert config found")

    from ..notifications.email_sender import send_alert_email
    smtp_config = {
        "host": alert.smtp_host,
        "port": alert.smtp_port,
        "user": alert.smtp_user,
        "password": alert.smtp_password,
    }
    test_stats = {
        "crawl_id": 0,
        "crawled_urls": 42,
        "critical_issues": 3,
        "warning_issues": 7,
        "info_issues": 12,
        "completed_at": datetime.utcnow().strftime("%d.%m.%Y %H:%M"),
    }
    success = await send_alert_email(
        to_email=alert.email,
        project_name=project.name + " [TEST]",
        crawl_stats=test_stats,
        new_issues=[{"url": project.start_url, "type": "test_issue", "severity": "critical"}],
        smtp_config=smtp_config,
        dashboard_url=os.getenv("FRONTEND_URL", "http://localhost:3000"),
    )
    if success:
        return {"message": "Test email sent successfully to {}".format(alert.email)}
    raise HTTPException(status_code=500, detail="Failed to send test email. Check SMTP configuration.")
