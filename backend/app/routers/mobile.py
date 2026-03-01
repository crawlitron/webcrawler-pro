from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from urllib.parse import unquote
import logging

from ..database import get_db
from ..models import Project, Crawl, Page

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/projects/{project_id}/summary")
def get_mobile_summary(project_id: int, db: Session = Depends(get_db)):
    """Mobile score overview for all pages in latest crawl.
    Returns aggregate mobile scores, count of pages with issues, average score.
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        latest_crawl = (
            db.query(Crawl)
            .filter(Crawl.project_id == project_id, Crawl.status == "completed")
            .order_by(desc(Crawl.finished_at))
            .first()
        )

        if not latest_crawl:
            return {
                "project_id": project_id,
                "crawl_id": None,
                "total_pages": 0,
                "pages_with_issues": 0,
                "average_score": 0,
                "score_distribution": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
            }

        pages = db.query(Page).filter(Page.crawl_id == latest_crawl.id).all()

        if not pages:
            return {
                "project_id": project_id,
                "crawl_id": latest_crawl.id,
                "total_pages": 0,
                "pages_with_issues": 0,
                "average_score": 0,
                "score_distribution": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
            }

        total_score = 0
        pages_with_issues = 0
        score_dist = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}

        for page in pages:
            extra = page.extra_data or {}
            mobile_check = extra.get("mobile_check", {})
            score = mobile_check.get("mobile_score", 0)
            issues = mobile_check.get("mobile_issues", [])

            total_score += score
            if issues:
                pages_with_issues += 1

            if score <= 20:
                score_dist["0-20"] += 1
            elif score <= 40:
                score_dist["21-40"] += 1
            elif score <= 60:
                score_dist["41-60"] += 1
            elif score <= 80:
                score_dist["61-80"] += 1
            else:
                score_dist["81-100"] += 1

        avg_score = round(total_score / len(pages), 2) if pages else 0

        return {
            "project_id": project_id,
            "crawl_id": latest_crawl.id,
            "total_pages": len(pages),
            "pages_with_issues": pages_with_issues,
            "average_score": avg_score,
            "score_distribution": score_dist,
        }

    except Exception as e:
        logger.warning("Error in get_mobile_summary: {}".format(str(e)))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/projects/{project_id}/issues")
def get_mobile_issues(
    project_id: int,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    sort_by: str = "score",
    order: str = "asc",
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all pages with mobile issues, filtered and sorted.
    Query params:
    - min_score: Filter pages with score >= this value
    - max_score: Filter pages with score <= this value
    - sort_by: 'score' | 'issues_count' | 'url'
    - order: 'asc' | 'desc'
    - limit: Max results (default 100)
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        latest_crawl = (
            db.query(Crawl)
            .filter(Crawl.project_id == project_id, Crawl.status == "completed")
            .order_by(desc(Crawl.finished_at))
            .first()
        )

        if not latest_crawl:
            return {"crawl_id": None, "pages": []}

        pages = db.query(Page).filter(Page.crawl_id == latest_crawl.id).all()

        results = []
        for page in pages:
            extra = page.extra_data or {}
            mobile_check = extra.get("mobile_check", {})
            score = mobile_check.get("mobile_score", 0)
            issues = mobile_check.get("mobile_issues", [])

            if min_score is not None and score < min_score:
                continue
            if max_score is not None and score > max_score:
                continue

            results.append({
                "page_id": page.id,
                "url": page.url,
                "mobile_score": score,
                "issues_count": len(issues),
                "mobile_issues": issues,
                "mobile_check": mobile_check,
            })

        # Sort results
        reverse = order == "desc"
        if sort_by == "score":
            results.sort(key=lambda x: x["mobile_score"], reverse=reverse)
        elif sort_by == "issues_count":
            results.sort(key=lambda x: x["issues_count"], reverse=reverse)
        elif sort_by == "url":
            results.sort(key=lambda x: x["url"], reverse=reverse)

        # Limit results
        results = results[:limit]

        return {
            "crawl_id": latest_crawl.id,
            "pages": results,
            "total_count": len(results),
        }

    except Exception as e:
        logger.warning("Error in get_mobile_issues: {}".format(str(e)))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/crawls/{crawl_id}/page/{url:path}")
def get_page_mobile_details(crawl_id: int, url: str, db: Session = Depends(get_db)):
    """Get mobile analysis details for a specific URL.
    URL parameter should be URL-encoded.
    """
    try:
        # Decode URL
        decoded_url = unquote(url)

        page = (
            db.query(Page)
            .filter(Page.crawl_id == crawl_id, Page.url == decoded_url)
            .first()
        )

        if not page:
            raise HTTPException(status_code=404, detail="Page not found")

        extra = page.extra_data or {}
        mobile_check = extra.get("mobile_check", {})

        return {
            "page_id": page.id,
            "crawl_id": crawl_id,
            "url": page.url,
            "mobile_check": mobile_check,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Error in get_page_mobile_details: {}".format(str(e)))
        raise HTTPException(status_code=500, detail="Internal server error")
