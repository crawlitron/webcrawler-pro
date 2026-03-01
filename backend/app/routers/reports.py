from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, HTMLResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Crawl, Page, Issue, Project

router = APIRouter(prefix="/api/crawls", tags=["reports"])


@router.get("/{crawl_id}/report/pdf")
def download_pdf_report(crawl_id: int, db: Session = Depends(get_db)):
    """Generate and download a PDF report for a crawl."""
    crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()
    if not crawl:
        raise HTTPException(status_code=404, detail="Crawl not found")
    project = db.query(Project).filter(Project.id == crawl.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pages = db.query(Page).filter(Page.crawl_id == crawl_id).all()
    issues = db.query(Issue).filter(Issue.crawl_id == crawl_id).all()

    try:
        from ..reports.pdf_generator import generate_crawl_pdf
        pdf_bytes = generate_crawl_pdf(crawl, pages, issues, project)
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="reportlab not installed. Run: pip install reportlab>=4.0.0"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="PDF generation failed: {}".format(str(e)))

    filename = "webcrawler-report-crawl-{}.pdf".format(crawl_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename={}".format(filename)},
    )


@router.get("/{crawl_id}/report/html", response_class=HTMLResponse)
def preview_html_report(crawl_id: int, db: Session = Depends(get_db)):
    """Generate an HTML preview report for a crawl."""
    crawl = db.query(Crawl).filter(Crawl.id == crawl_id).first()
    if not crawl:
        raise HTTPException(status_code=404, detail="Crawl not found")
    project = db.query(Project).filter(Project.id == crawl.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pages = db.query(Page).filter(Page.crawl_id == crawl_id).all()
    issues = db.query(Issue).filter(Issue.crawl_id == crawl_id).all()

    from ..reports.pdf_generator import generate_html_report
    html = generate_html_report(crawl, pages, issues, project)
    return HTMLResponse(content=html)
