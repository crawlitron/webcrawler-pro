import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def _build_html_email(project_name: str, crawl_stats: dict, new_issues: list, dashboard_url: str = "") -> str:
    """Build styled HTML email body."""
    crawled = crawl_stats.get("crawled_urls", 0)
    critical = crawl_stats.get("critical_issues", 0)
    warning = crawl_stats.get("warning_issues", 0)
    info = crawl_stats.get("info_issues", 0)
    crawl_id = crawl_stats.get("crawl_id", "")
    completed = crawl_stats.get("completed_at", datetime.utcnow().strftime("%d.%m.%Y %H:%M"))

    issues_rows = ""
    for iss in new_issues[:20]:
        severity = iss.get("severity", "info")
        color = {"critical": "#fee2e2", "warning": "#fef9c3", "info": "#dbeafe"}.get(severity, "#f9fafb")
        badge_color = {"critical": "#b91c1c", "warning": "#854d0e", "info": "#1d4ed8"}.get(severity, "#374151")
        url = iss.get("url", "")[:80]
        itype = iss.get("type", "").replace("_", " ").title()
        issues_rows += (
            "<tr style='background:{bg}'>"
            "<td style='padding:8px 12px'><span style='background:{bc};color:white;padding:2px 8px;"
            "border-radius:4px;font-size:12px'>{sev}</span></td>"
            "<td style='padding:8px 12px;font-size:13px'>{itype}</td>"
            "<td style='padding:8px 12px;font-size:12px;color:#6b7280'>{url}</td>"
            "</tr>"
        ).format(bg=color, bc=badge_color, sev=severity.upper(), itype=itype, url=url)

    dashboard_btn = ""
    if dashboard_url:
        dashboard_btn = (
            "<p style='text-align:center;margin:24px 0'>"
            "<a href='{url}' style='background:#1e40af;color:white;padding:12px 24px;"
            "border-radius:6px;text-decoration:none;font-weight:bold'>Dashboard öffnen</a></p>"
        ).format(url=dashboard_url)

    html = """<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"><title>WebCrawler Pro Alert</title></head>
<body style="font-family:Arial,sans-serif;background:#f3f4f6;margin:0;padding:0">
<div style="max-width:600px;margin:0 auto;background:white;border-radius:8px;overflow:hidden;margin-top:24px">
  <div style="background:#1e40af;padding:24px;text-align:center">
    <h1 style="color:white;margin:0;font-size:22px">&#x1F916; WebCrawler Pro</h1>
    <p style="color:#bfdbfe;margin:4px 0 0">Crawl-Benachrichtigung</p>
  </div>
  <div style="padding:24px">
    <h2 style="color:#1e3a5f;margin-top:0">Crawl abgeschlossen: {project_name}</h2>
    <p style="color:#6b7280">Abgeschlossen am {completed}</p>
    <div style="display:flex;gap:12px;margin:16px 0">
      <div style="flex:1;background:#dbeafe;border-radius:8px;padding:16px;text-align:center">
        <div style="font-size:28px;font-weight:bold;color:#1e40af">{crawled}</div>
        <div style="font-size:12px;color:#6b7280">URLs gecrawlt</div>
      </div>
      <div style="flex:1;background:#fee2e2;border-radius:8px;padding:16px;text-align:center">
        <div style="font-size:28px;font-weight:bold;color:#b91c1c">{critical}</div>
        <div style="font-size:12px;color:#6b7280">Kritisch</div>
      </div>
      <div style="flex:1;background:#fef9c3;border-radius:8px;padding:16px;text-align:center">
        <div style="font-size:28px;font-weight:bold;color:#854d0e">{warning}</div>
        <div style="font-size:12px;color:#6b7280">Warnungen</div>
      </div>
      <div style="flex:1;background:#f0fdf4;border-radius:8px;padding:16px;text-align:center">
        <div style="font-size:28px;font-weight:bold;color:#166534">{info}</div>
        <div style="font-size:12px;color:#6b7280">Infos</div>
      </div>
    </div>
    {issues_section}
    {dashboard_btn}
    <hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0">
    <p style="color:#9ca3af;font-size:12px;text-align:center">
      Diese E-Mail wurde von WebCrawler Pro gesendet.<br>
      Um Benachrichtigungen zu deaktivieren, gehe zu Projekteinstellungen &rarr; Alerts.
    </p>
  </div>
</div>
</body></html>""".format(
        project_name=project_name,
        completed=completed,
        crawled=crawled,
        critical=critical,
        warning=warning,
        info=info,
        issues_section=(
            "<h3 style='color:#1e3a5f'>Neue kritische Issues ({count})</h3>"
            "<table style='width:100%;border-collapse:collapse'>"
            "<tr style='background:#f9fafb'><th style='padding:8px 12px;text-align:left'>Schwere</th>"
            "<th style='padding:8px 12px;text-align:left'>Typ</th>"
            "<th style='padding:8px 12px;text-align:left'>URL</th></tr>"
            "{rows}</table>"
        ).format(count=len(new_issues), rows=issues_rows) if new_issues else "",
        dashboard_btn=dashboard_btn,
    )
    return html


async def send_alert_email(
    to_email: str,
    project_name: str,
    crawl_stats: dict,
    new_issues: list,
    smtp_config: dict,
    dashboard_url: str = "",
) -> bool:
    """
    Send HTML alert email via aiosmtplib.
    smtp_config keys: host, port, user, password, from_addr, use_tls
    Returns True on success, False on failure.
    """
    try:
        import aiosmtplib
    except ImportError:
        logger.error("aiosmtplib not installed. Run: pip install aiosmtplib>=3.0.0")
        return False

    host = smtp_config.get("host") or os.getenv("SMTP_HOST", "")
    port = int(smtp_config.get("port") or os.getenv("SMTP_PORT", "587"))
    user = smtp_config.get("user") or os.getenv("SMTP_USER", "")
    password = smtp_config.get("password") or os.getenv("SMTP_PASSWORD", "")
    from_addr = smtp_config.get("from_addr") or os.getenv("SMTP_FROM", user)
    use_tls = smtp_config.get("use_tls", port == 465)

    if not host:
        logger.warning("SMTP host not configured, skipping email alert")
        return False

    html_body = _build_html_email(project_name, crawl_stats, new_issues, dashboard_url)
    critical = crawl_stats.get("critical_issues", 0)
    subject = "[WebCrawler Pro] {name} — {crit} kritische Issues gefunden".format(
        name=project_name, crit=critical
    ) if critical > 0 else "[WebCrawler Pro] Crawl abgeschlossen: {}".format(project_name)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if use_tls:
            await aiosmtplib.send(
                msg,
                hostname=host,
                port=port,
                username=user or None,
                password=password or None,
                use_tls=True,
            )
        else:
            await aiosmtplib.send(
                msg,
                hostname=host,
                port=port,
                username=user or None,
                password=password or None,
                start_tls=True,
            )
        logger.info("Alert email sent to %s for project %s", to_email, project_name)
        return True
    except Exception as e:
        logger.error("Failed to send alert email to %s: %s", to_email, e)
        return False


def send_alert_email_sync(
    to_email: str,
    project_name: str,
    crawl_stats: dict,
    new_issues: list,
    smtp_config: dict,
    dashboard_url: str = "",
) -> bool:
    """Synchronous wrapper for use in Celery tasks."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(
            send_alert_email(to_email, project_name, crawl_stats, new_issues, smtp_config, dashboard_url)
        )
    except Exception as e:
        logger.error("send_alert_email_sync failed: %s", e)
        return False
