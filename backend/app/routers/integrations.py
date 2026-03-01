import os
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import GSCConnection, KeywordRanking, Project, User
from .auth import get_db, require_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["integrations"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:44544/api/integrations/gsc/callback"
)


class GSCSiteLink(BaseModel):
    site_url: str


# ── OAuth2 Flow ────────────────────────────────────────────────────────

@router.get("/api/integrations/gsc/auth-url")
def gsc_auth_url(current_user: User = Depends(require_user)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured — set GOOGLE_CLIENT_ID in .env")
    try:
        from ..integrations.google_search_console import get_oauth_flow
        flow = get_oauth_flow(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI)
        auth_url, _ = flow.authorization_url(
            access_type="offline", prompt="consent",
            state=str(current_user.id)
        )
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/api/integrations/gsc/callback")
def gsc_callback(
    code: str = Query(...),
    state: str = Query(default=""),
    db: Session = Depends(get_db),
):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured")
    try:
        from ..integrations.google_search_console import get_oauth_flow
        flow = get_oauth_flow(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI)
        flow.fetch_token(code=code)
        creds = flow.credentials
        user_id = int(state) if state.isdigit() else None
        if not user_id:
            raise HTTPException(400, "Invalid state parameter")
        existing = db.query(GSCConnection).filter(GSCConnection.user_id == user_id).first()
        if existing:
            existing.access_token = creds.token
            existing.refresh_token = creds.refresh_token or existing.refresh_token
            existing.token_expiry = creds.expiry
        else:
            db.add(GSCConnection(
                user_id=user_id,
                site_url="",
                access_token=creds.token,
                refresh_token=creds.refresh_token,
                token_expiry=creds.expiry,
            ))
        db.commit()
        return RedirectResponse(url="/settings/integrations?gsc=connected")
    except Exception as e:
        logger.error("GSC callback error: %s", e)
        return RedirectResponse(url="/settings/integrations?gsc=error")


@router.delete("/api/integrations/gsc/disconnect")
def gsc_disconnect(current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    conn = db.query(GSCConnection).filter(GSCConnection.user_id == current_user.id).first()
    if conn:
        db.delete(conn)
        db.commit()
    return {"message": "GSC disconnected"}


@router.get("/api/integrations/gsc/status")
def gsc_status(current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    conn = db.query(GSCConnection).filter(GSCConnection.user_id == current_user.id).first()
    return {
        "connected": conn is not None,
        "site_url": conn.site_url if conn else None,
        "token_expiry": conn.token_expiry if conn else None,
    }


@router.get("/api/integrations/gsc/sites")
def gsc_sites(current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    conn = db.query(GSCConnection).filter(GSCConnection.user_id == current_user.id).first()
    if not conn:
        raise HTTPException(404, "GSC not connected")
    try:
        from ..integrations.google_search_console import GSCClient
        client = GSCClient(conn.access_token, conn.refresh_token, conn.token_expiry)
        return {"sites": client.get_sites()}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Project GSC Endpoints ─────────────────────────────────────────────

@router.post("/api/projects/{project_id}/integrations/gsc")
def link_gsc_site(
    project_id: int, data: GSCSiteLink,
    current_user: User = Depends(require_user), db: Session = Depends(get_db)
):
    conn = db.query(GSCConnection).filter(GSCConnection.user_id == current_user.id).first()
    if not conn:
        raise HTTPException(404, "GSC not connected")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    conn.project_id = project_id
    conn.site_url = data.site_url
    db.commit()
    return {"message": "GSC site linked", "site_url": data.site_url}


@router.get("/api/projects/{project_id}/gsc/analytics")
def gsc_analytics(
    project_id: int,
    days: int = Query(default=28, ge=1, le=90),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    conn = db.query(GSCConnection).filter(
        GSCConnection.user_id == current_user.id,
        GSCConnection.project_id == project_id,
    ).first()
    if not conn:
        raise HTTPException(404, "GSC not linked to this project")
    try:
        from ..integrations.google_search_console import GSCClient
        from datetime import timedelta
        client = GSCClient(conn.access_token, conn.refresh_token, conn.token_expiry)
        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = client.get_search_analytics(conn.site_url, start, end, ["page", "date"])
        total_clicks = sum(r.get("clicks", 0) for r in rows)
        total_impressions = sum(r.get("impressions", 0) for r in rows)
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0
        avg_position = (sum(r.get("position", 0) for r in rows) / len(rows)) if rows else 0
        return {
            "site_url": conn.site_url,
            "period_days": days,
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "avg_ctr": round(avg_ctr, 2),
            "avg_position": round(avg_position, 1),
            "rows": rows[:100],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/api/projects/{project_id}/gsc/keywords")
def gsc_keywords(
    project_id: int,
    days: int = Query(default=90, ge=1, le=365),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    rankings = db.query(KeywordRanking).filter(
        KeywordRanking.project_id == project_id
    ).order_by(KeywordRanking.date.desc(), KeywordRanking.clicks.desc()).limit(limit).all()
    return [{"keyword": r.keyword, "date": str(r.date), "position": r.position,
             "clicks": r.clicks, "impressions": r.impressions, "ctr": r.ctr, "url": r.url}
            for r in rankings]


@router.get("/api/projects/{project_id}/gsc/coverage")
def gsc_coverage(
    project_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    conn = db.query(GSCConnection).filter(
        GSCConnection.user_id == current_user.id,
        GSCConnection.project_id == project_id,
    ).first()
    if not conn:
        raise HTTPException(404, "GSC not linked to this project")
    try:
        from ..integrations.google_search_console import GSCClient
        client = GSCClient(conn.access_token, conn.refresh_token, conn.token_expiry)
        sitemaps = client.get_sitemaps(conn.site_url)
        return {"site_url": conn.site_url, "sitemaps": sitemaps}
    except Exception as e:
        raise HTTPException(500, str(e))


# ═══════════════════════════════════════════════════════════════════════
# v0.9.0 Feature: Google Analytics 4 Integration
# ═══════════════════════════════════════════════════════════════════════

@router.get("/api/integrations/ga4/auth-url")
async def ga4_auth_url(
    project_id: int = Query(...),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get GA4 OAuth2 authorization URL."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured — set GOOGLE_CLIENT_ID in .env")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    
    try:
        from ..integrations.google_analytics import GA4Integration
        ga4 = GA4Integration(db)
        auth_url = await ga4.get_auth_url(
            project_id=project_id,
            redirect_uri=os.getenv(
                "GA4_REDIRECT_URI",
                "http://localhost:44544/api/integrations/ga4/callback"
            ),
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error("GA4 auth URL error: %s", e)
        raise HTTPException(500, str(e))


@router.get("/api/integrations/ga4/callback")
async def ga4_callback(
    code: str = Query(...),
    state: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """Handle GA4 OAuth2 callback."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured")
    
    try:
        project_id = int(state) if state.isdigit() else None
        if not project_id:
            raise HTTPException(400, "Invalid state parameter")
        
        from ..integrations.google_analytics import GA4Integration
        ga4 = GA4Integration(db)
        result = await ga4.handle_callback(
            code=code,
            project_id=project_id,
            redirect_uri=os.getenv(
                "GA4_REDIRECT_URI",
                "http://localhost:44544/api/integrations/ga4/callback"
            ),
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )
        return RedirectResponse(url=f"/projects/{project_id}/settings?ga4=connected")
    except Exception as e:
        logger.error("GA4 callback error: %s", e)
        return RedirectResponse(url="/settings/integrations?ga4=error")


@router.delete("/api/projects/{project_id}/integrations/ga4")
async def ga4_disconnect(
    project_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Disconnect GA4 integration."""
    from ..models import GA4Token, GA4Metric
    
    token = db.query(GA4Token).filter(GA4Token.project_id == project_id).first()
    if token:
        db.query(GA4Metric).filter(GA4Metric.project_id == project_id).delete()
        db.delete(token)
        db.commit()
    
    return {"message": "GA4 disconnected"}


@router.get("/api/projects/{project_id}/ga4/status")
async def ga4_status(
    project_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get GA4 connection status."""
    from ..models import GA4Token
    
    token = db.query(GA4Token).filter(GA4Token.project_id == project_id).first()
    return {
        "connected": token is not None,
        "property_id": token.property_id if token else None,
        "expires_at": token.expires_at if token else None,
    }


@router.get("/api/projects/{project_id}/ga4/overview")
async def ga4_overview(
    project_id: int,
    date_range: str = Query(default="last30days"),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get GA4 KPI overview."""
    from ..models import GA4Token
    
    token = db.query(GA4Token).filter(GA4Token.project_id == project_id).first()
    if not token:
        raise HTTPException(404, "GA4 not connected to this project")
    
    try:
        from ..integrations.google_analytics import GA4Integration
        ga4 = GA4Integration(db)
        overview = await ga4.get_overview(
            property_id=token.property_id,
            date_range=date_range
        )
        return overview
    except Exception as e:
        logger.error("GA4 overview error: %s", e)
        raise HTTPException(500, str(e))


@router.get("/api/projects/{project_id}/ga4/top-pages")
async def ga4_top_pages(
    project_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    date_range: str = Query(default="last30days"),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get top pages by sessions."""
    from ..models import GA4Token
    
    token = db.query(GA4Token).filter(GA4Token.project_id == project_id).first()
    if not token:
        raise HTTPException(404, "GA4 not connected to this project")
    
    try:
        from ..integrations.google_analytics import GA4Integration
        ga4 = GA4Integration(db)
        pages = await ga4.get_top_pages(
            property_id=token.property_id,
            limit=limit,
            date_range=date_range
        )
        return {"pages": pages}
    except Exception as e:
        logger.error("GA4 top pages error: %s", e)
        raise HTTPException(500, str(e))


@router.get("/api/projects/{project_id}/ga4/sources")
async def ga4_traffic_sources(
    project_id: int,
    date_range: str = Query(default="last30days"),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get traffic sources breakdown."""
    from ..models import GA4Token
    
    token = db.query(GA4Token).filter(GA4Token.project_id == project_id).first()
    if not token:
        raise HTTPException(404, "GA4 not connected to this project")
    
    try:
        from ..integrations.google_analytics import GA4Integration
        ga4 = GA4Integration(db)
        sources = await ga4.get_traffic_sources(
            property_id=token.property_id,
            date_range=date_range
        )
        return {"sources": sources}
    except Exception as e:
        logger.error("GA4 traffic sources error: %s", e)
        raise HTTPException(500, str(e))


@router.get("/api/projects/{project_id}/ga4/devices")
async def ga4_device_breakdown(
    project_id: int,
    date_range: str = Query(default="last30days"),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get device category breakdown."""
    from ..models import GA4Token
    
    token = db.query(GA4Token).filter(GA4Token.project_id == project_id).first()
    if not token:
        raise HTTPException(404, "GA4 not connected to this project")
    
    try:
        from ..integrations.google_analytics import GA4Integration
        ga4 = GA4Integration(db)
        devices = await ga4.get_device_breakdown(
            property_id=token.property_id,
            date_range=date_range
        )
        return {"devices": devices}
    except Exception as e:
        logger.error("GA4 device breakdown error: %s", e)
        raise HTTPException(500, str(e))


@router.get("/api/projects/{project_id}/ga4/conversions")
async def ga4_conversion_events(
    project_id: int,
    date_range: str = Query(default="last30days"),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get conversion events."""
    from ..models import GA4Token
    
    token = db.query(GA4Token).filter(GA4Token.project_id == project_id).first()
    if not token:
        raise HTTPException(404, "GA4 not connected to this project")
    
    try:
        from ..integrations.google_analytics import GA4Integration
        ga4 = GA4Integration(db)
        events = await ga4.get_conversion_events(
            property_id=token.property_id,
            date_range=date_range
        )
        return {"events": events}
    except Exception as e:
        logger.error("GA4 conversion events error: %s", e)
        raise HTTPException(500, str(e))


@router.post("/api/projects/{project_id}/ga4/sync")
async def ga4_manual_sync(
    project_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Trigger manual GA4 data sync."""
    from ..models import GA4Token
    
    token = db.query(GA4Token).filter(GA4Token.project_id == project_id).first()
    if not token:
        raise HTTPException(404, "GA4 not connected to this project")
    
    try:
        from ..crawler.scheduled_tasks import sync_ga4_data
        sync_ga4_data.delay(project_id)
        return {"message": "GA4 sync triggered", "project_id": project_id}
    except Exception as e:
        logger.error("GA4 manual sync error: %s", e)
        raise HTTPException(500, str(e))
