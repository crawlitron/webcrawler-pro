import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

GSC_AVAILABLE = False
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    GSC_AVAILABLE = True
except ImportError:
    logger.warning("google-api-python-client not installed — GSC integration disabled")

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def get_oauth_flow(client_id: str, client_secret: str, redirect_uri: str):
    if not GSC_AVAILABLE:
        raise RuntimeError("GSC dependencies not installed")
    return Flow.from_client_config(
        {"web": {"client_id": client_id, "client_secret": client_secret,
                 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                 "token_uri": "https://oauth2.googleapis.com/token"}},
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )


class GSCClient:
    def __init__(self, access_token: str, refresh_token: Optional[str] = None,
                 token_expiry: Optional[datetime] = None):
        if not GSC_AVAILABLE:
            raise RuntimeError("GSC dependencies not installed")
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=None,
            client_secret=None,
            scopes=SCOPES,
        )
        self.service = build("searchconsole", "v1", credentials=self.creds)

    def get_sites(self) -> list:
        try:
            result = self.service.sites().list().execute()
            return result.get("siteEntry", [])
        except Exception as e:
            logger.error("GSC get_sites error: %s", e)
            return []

    def get_search_analytics(
        self, site_url: str, start_date: str, end_date: str,
        dimensions: list = None, row_limit: int = 1000
    ) -> list:
        if dimensions is None:
            dimensions = ["query", "page"]
        try:
            body = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": dimensions,
                "rowLimit": row_limit,
            }
            result = self.service.searchanalytics().query(siteUrl=site_url, body=body).execute()
            rows = result.get("rows", [])
            output = []
            for row in rows:
                keys = row.get("keys", [])
                item = {"clicks": row.get("clicks", 0), "impressions": row.get("impressions", 0),
                        "ctr": row.get("ctr", 0.0), "position": row.get("position", 0.0)}
                for i, dim in enumerate(dimensions):
                    item[dim] = keys[i] if i < len(keys) else None
                output.append(item)
            return output
        except Exception as e:
            logger.error("GSC get_search_analytics error: %s", e)
            return []

    def get_keyword_rankings(self, site_url: str, days: int = 90) -> list:
        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        return self.get_search_analytics(site_url, start, end,
                                         dimensions=["query", "page", "date"], row_limit=5000)

    def get_coverage_issues(self, site_url: str) -> list:
        try:
            result = self.service.urlInspection().index().inspect(
                body={"inspectionUrl": site_url, "siteUrl": site_url}
            ).execute()
            return result.get("inspectionResult", {}).get("indexStatusResult", {})
        except Exception as e:
            logger.error("GSC coverage error: %s", e)
            return []

    def get_sitemaps(self, site_url: str) -> list:
        try:
            result = self.service.sitemaps().list(siteUrl=site_url).execute()
            return result.get("sitemap", [])
        except Exception as e:
            logger.error("GSC sitemaps error: %s", e)
            return []
