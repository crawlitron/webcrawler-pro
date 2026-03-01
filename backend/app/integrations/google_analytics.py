import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

GA4_AVAILABLE = False
try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest,
        DateRange,
        Dimension,
        Metric,
        FilterExpression,
        Filter,
    )
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    GA4_AVAILABLE = True
except ImportError:
    logger.warning("google-analytics-data not installed — GA4 integration disabled")

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def get_oauth_flow(client_id: str, client_secret: str, redirect_uri: str):
    """Create OAuth2 flow for GA4 authentication."""
    if not GA4_AVAILABLE:
        raise RuntimeError("GA4 dependencies not installed")
    return Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )


class GA4Integration:
    """Google Analytics 4 Data API Integration."""

    SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

    def __init__(self, db: Session):
        """Initialize GA4 integration with database session."""
        if not GA4_AVAILABLE:
            raise RuntimeError("GA4 dependencies not installed")
        self.db = db

    def _get_client(self, credentials: Credentials) -> BetaAnalyticsDataClient:
        """Create GA4 Data API client with credentials."""
        return BetaAnalyticsDataClient(credentials=credentials)

    def _load_credentials(self, project_id: int) -> Optional[Credentials]:
        """Load credentials from database for given project."""
        from ..models import GA4Token

        token = self.db.query(GA4Token).filter(GA4Token.project_id == project_id).first()
        if not token:
            return None

        creds = Credentials(
            token=token.access_token,
            refresh_token=token.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=None,
            client_secret=None,
            scopes=self.SCOPES,
        )
        return creds

    def _parse_date_range(self, date_range: str) -> Tuple[str, str]:
        """Convert date range string to start/end dates.
        
        Args:
            date_range: String like 'last7days', 'last30days', 'last90days'
            
        Returns:
            Tuple of (start_date, end_date) in YYYY-MM-DD format
        """
        end_date = datetime.utcnow()
        
        if date_range == "last7days":
            start_date = end_date - timedelta(days=7)
        elif date_range == "last30days":
            start_date = end_date - timedelta(days=30)
        elif date_range == "last90days":
            start_date = end_date - timedelta(days=90)
        elif date_range == "yesterday":
            start_date = end_date - timedelta(days=1)
            end_date = start_date
        else:
            start_date = end_date - timedelta(days=30)

        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    async def get_auth_url(self, project_id: int, redirect_uri: str, client_id: str, client_secret: str) -> str:
        """Generate OAuth2 authorization URL.
        
        Args:
            project_id: Project ID to associate with the token
            redirect_uri: OAuth redirect URI
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            
        Returns:
            Authorization URL string
        """
        flow = get_oauth_flow(client_id, client_secret, redirect_uri)
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            state=str(project_id),
        )
        return auth_url

    async def handle_callback(self, code: str, project_id: int, redirect_uri: str, 
                            client_id: str, client_secret: str) -> Dict:
        """Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from OAuth callback
            project_id: Project ID to associate tokens with
            redirect_uri: OAuth redirect URI
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            
        Returns:
            Dict with property_id and connection status
        """
        from ..models import GA4Token

        flow = get_oauth_flow(client_id, client_secret, redirect_uri)
        flow.fetch_token(code=code)
        creds = flow.credentials

        client = self._get_client(creds)
        
        try:
            from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
            admin_client = AnalyticsAdminServiceClient(credentials=creds)
            accounts = admin_client.list_accounts()
            
            property_id = None
            for account in accounts:
                properties = admin_client.list_properties(parent=account.name)
                for prop in properties:
                    property_id = prop.name.split("/")[-1]
                    break
                if property_id:
                    break
                    
            if not property_id:
                property_id = "properties/0"
                
        except Exception as e:
            logger.warning("Could not fetch property ID: %s", e)
            property_id = "properties/0"

        existing = self.db.query(GA4Token).filter(GA4Token.project_id == project_id).first()
        if existing:
            existing.access_token = creds.token
            existing.refresh_token = creds.refresh_token or existing.refresh_token
            existing.property_id = property_id
            existing.expires_at = creds.expiry or datetime.utcnow() + timedelta(hours=1)
            existing.updated_at = datetime.utcnow()
        else:
            token = GA4Token(
                project_id=project_id,
                access_token=creds.token,
                refresh_token=creds.refresh_token,
                property_id=property_id,
                expires_at=creds.expiry or datetime.utcnow() + timedelta(hours=1),
            )
            self.db.add(token)

        self.db.commit()

        return {
            "property_id": property_id,
            "connected": True,
        }

    async def get_overview(self, property_id: str, date_range: str = "last30days") -> Dict:
        """Get overview KPIs: sessions, pageviews, bounce_rate, avg_duration.
        
        Args:
            property_id: GA4 property ID
            date_range: Date range string (e.g., 'last30days')
            
        Returns:
            Dict with overview metrics
        """
        from ..models import GA4Token

        token = self.db.query(GA4Token).filter(GA4Token.property_id == property_id).first()
        if not token:
            raise ValueError("GA4 token not found for property")

        creds = self._load_credentials(token.project_id)
        client = self._get_client(creds)

        start_date, end_date = self._parse_date_range(date_range)

        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="screenPageViews"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
                Metric(name="conversions"),
            ],
        )

        try:
            response = client.run_report(request)
            
            if response.rows:
                row = response.rows[0]
                return {
                    "sessions": int(row.metric_values[0].value),
                    "total_users": int(row.metric_values[1].value),
                    "pageviews": int(row.metric_values[2].value),
                    "bounce_rate": float(row.metric_values[3].value),
                    "avg_duration": float(row.metric_values[4].value),
                    "conversions": int(row.metric_values[5].value),
                    "date_range": date_range,
                }
            else:
                return {
                    "sessions": 0,
                    "total_users": 0,
                    "pageviews": 0,
                    "bounce_rate": 0.0,
                    "avg_duration": 0.0,
                    "conversions": 0,
                    "date_range": date_range,
                }
        except Exception as e:
            logger.error("GA4 get_overview error: %s", e)
            raise

    async def get_top_pages(self, property_id: str, limit: int = 10, 
                          date_range: str = "last30days") -> List[Dict]:
        """Get top pages by sessions/pageviews.
        
        Args:
            property_id: GA4 property ID
            limit: Maximum number of pages to return
            date_range: Date range string
            
        Returns:
            List of dicts with page data
        """
        from ..models import GA4Token

        token = self.db.query(GA4Token).filter(GA4Token.property_id == property_id).first()
        if not token:
            raise ValueError("GA4 token not found for property")

        creds = self._load_credentials(token.project_id)
        client = self._get_client(creds)

        start_date, end_date = self._parse_date_range(date_range)

        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="pagePath")],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="sessions"),
                Metric(name="averageSessionDuration"),
            ],
            limit=limit,
            order_bys=[
                {"metric": {"metric_name": "screenPageViews"}, "desc": True}
            ],
        )

        try:
            response = client.run_report(request)
            
            results = []
            for row in response.rows:
                results.append({
                    "page_path": row.dimension_values[0].value,
                    "pageviews": int(row.metric_values[0].value),
                    "sessions": int(row.metric_values[1].value),
                    "avg_duration": float(row.metric_values[2].value),
                })
            return results
        except Exception as e:
            logger.error("GA4 get_top_pages error: %s", e)
            raise

    async def get_traffic_sources(self, property_id: str, 
                                 date_range: str = "last30days") -> Dict:
        """Get traffic breakdown by source/medium.
        
        Args:
            property_id: GA4 property ID
            date_range: Date range string
            
        Returns:
            Dict grouped by source/medium
        """
        from ..models import GA4Token

        token = self.db.query(GA4Token).filter(GA4Token.property_id == property_id).first()
        if not token:
            raise ValueError("GA4 token not found for property")

        creds = self._load_credentials(token.project_id)
        client = self._get_client(creds)

        start_date, end_date = self._parse_date_range(date_range)

        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[
                Dimension(name="sessionSource"),
                Dimension(name="sessionMedium"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="newUsers"),
            ],
        )

        try:
            response = client.run_report(request)
            
            sources = {}
            for row in response.rows:
                source = row.dimension_values[0].value
                medium = row.dimension_values[1].value
                key = f"{source} / {medium}"
                sources[key] = {
                    "sessions": int(row.metric_values[0].value),
                    "new_users": int(row.metric_values[1].value),
                }
            return sources
        except Exception as e:
            logger.error("GA4 get_traffic_sources error: %s", e)
            raise

    async def get_device_breakdown(self, property_id: str, 
                                  date_range: str = "last30days") -> Dict:
        """Get sessions by device category.
        
        Args:
            property_id: GA4 property ID
            date_range: Date range string
            
        Returns:
            Dict: {desktop: N, mobile: N, tablet: N}
        """
        from ..models import GA4Token

        token = self.db.query(GA4Token).filter(GA4Token.property_id == property_id).first()
        if not token:
            raise ValueError("GA4 token not found for property")

        creds = self._load_credentials(token.project_id)
        client = self._get_client(creds)

        start_date, end_date = self._parse_date_range(date_range)

        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="deviceCategory")],
            metrics=[Metric(name="sessions")],
        )

        try:
            response = client.run_report(request)
            
            devices = {"desktop": 0, "mobile": 0, "tablet": 0}
            for row in response.rows:
                category = row.dimension_values[0].value.lower()
                sessions = int(row.metric_values[0].value)
                if category in devices:
                    devices[category] = sessions
            return devices
        except Exception as e:
            logger.error("GA4 get_device_breakdown error: %s", e)
            raise

    async def get_conversion_events(self, property_id: str, 
                                   date_range: str = "last30days") -> List[Dict]:
        """Get conversion events with counts.
        
        Args:
            property_id: GA4 property ID
            date_range: Date range string
            
        Returns:
            List of events with counts
        """
        from ..models import GA4Token

        token = self.db.query(GA4Token).filter(GA4Token.property_id == property_id).first()
        if not token:
            raise ValueError("GA4 token not found for property")

        creds = self._load_credentials(token.project_id)
        client = self._get_client(creds)

        start_date, end_date = self._parse_date_range(date_range)

        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="conversions")],
        )

        try:
            response = client.run_report(request)
            
            events = []
            for row in response.rows:
                event_name = row.dimension_values[0].value
                conversions = int(row.metric_values[0].value)
                if conversions > 0:
                    events.append({
                        "event_name": event_name,
                        "conversions": conversions,
                    })
            return sorted(events, key=lambda x: x["conversions"], reverse=True)
        except Exception as e:
            logger.error("GA4 get_conversion_events error: %s", e)
            raise

    async def sync_to_db(self, project_id: int) -> None:
        """Sync GA4 data to database (called by Celery task).
        
        Args:
            project_id: Project ID to sync data for
        """
        from ..models import GA4Token, GA4Metric
        from datetime import date

        token = self.db.query(GA4Token).filter(GA4Token.project_id == project_id).first()
        if not token:
            logger.warning("No GA4 token found for project %s", project_id)
            return

        try:
            top_pages = await self.get_top_pages(token.property_id, limit=100)
            
            today = date.today()
            
            for page_data in top_pages:
                metric = GA4Metric(
                    project_id=project_id,
                    date=today,
                    page_path=page_data["page_path"],
                    sessions=page_data["sessions"],
                    pageviews=page_data["pageviews"],
                    avg_duration=page_data["avg_duration"],
                )
                self.db.add(metric)
            
            cutoff_date = today - timedelta(days=90)
            self.db.query(GA4Metric).filter(
                GA4Metric.project_id == project_id,
                GA4Metric.date < cutoff_date
            ).delete()
            
            self.db.commit()
            logger.info("GA4 sync completed for project %s", project_id)
            
        except Exception as e:
            logger.error("GA4 sync failed for project %s: %s", project_id, e)
            self.db.rollback()
