import logging
import requests
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
HEADERS = {"User-Agent": "WebCrawlerPro/2.0 (+https://webcrawlerpro.io/bot)"}


def _make_issue(severity: str, issue_type: str, description: str, recommendation: str = "") -> dict:
    return {
        "severity": severity,
        "type": issue_type,
        "description": description,
        "recommendation": recommendation,
    }


def analyze_robots_txt(base_url: str) -> dict:
    """
    Loads and analyzes robots.txt for a given base URL.
    Returns dict with found, content, sitemaps, disallowed_paths,
    crawl_delay, user_agents, issues.
    """
    parsed = urlparse(base_url)
    robots_url = "{}://{}/robots.txt".format(parsed.scheme, parsed.netloc)
    issues = []
    content = ""
    sitemaps = []
    disallowed_paths = []
    crawl_delay = None
    user_agents = []
    found = False

    try:
        resp = requests.get(robots_url, timeout=DEFAULT_TIMEOUT, headers=HEADERS, allow_redirects=True)
        if resp.status_code == 200:
            found = True
            content = resp.text

            # Parse with RobotFileParser
            rfp = RobotFileParser()
            rfp.set_url(robots_url)
            rfp.parse(content.splitlines())

            # Extract directives manually for full info
            current_agents = []
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" not in line:
                    continue
                key, _, val = line.partition(":")
                key = key.strip().lower()
                val = val.strip()
                if key == "user-agent":
                    current_agents.append(val)
                    if val not in user_agents:
                        user_agents.append(val)
                elif key == "disallow":
                    if val:
                        disallowed_paths.append(val)
                elif key == "crawl-delay":
                    try:
                        crawl_delay = float(val)
                    except ValueError:
                        pass
                elif key == "sitemap":
                    if val and val not in sitemaps:
                        sitemaps.append(val)

            # Check for wildcard user-agent
            if "*" not in user_agents:
                issues.append(_make_issue(
                    "warning",
                    "robots_no_wildcard_agent",
                    "robots.txt hat keinen User-agent: * Eintrag.",
                    "Füge einen User-agent: * Block hinzu, um alle Crawler anzusprechen."
                ))

            # Check sitemap reference
            if not sitemaps:
                issues.append(_make_issue(
                    "info",
                    "robots_no_sitemap",
                    "Kein Sitemap-Verweis in robots.txt gefunden.",
                    "Füge 'Sitemap: https://domain.de/sitemap.xml' in robots.txt ein."
                ))

            # Check if everything is blocked
            if "/" in disallowed_paths and "*" in user_agents:
                issues.append(_make_issue(
                    "critical",
                    "robots_all_blocked",
                    "robots.txt blockiert alle Crawler mit 'Disallow: /' für User-agent: *.",
                    "Überprüfe die robots.txt — alle Seiten sind für Suchmaschinen gesperrt."
                ))
        else:
            issues.append(_make_issue(
                "warning",
                "robots_not_found",
                "robots.txt nicht gefunden (HTTP {}).".format(resp.status_code),
                "Erstelle eine robots.txt Datei im Webroot."
            ))
    except requests.RequestException as e:
        issues.append(_make_issue(
            "warning",
            "robots_fetch_error",
            "robots.txt konnte nicht geladen werden: {}".format(str(e)),
            "Stelle sicher, dass robots.txt öffentlich erreichbar ist."
        ))

    return {
        "found": found,
        "url": robots_url,
        "content": content,
        "sitemaps": sitemaps,
        "disallowed_paths": disallowed_paths,
        "crawl_delay": crawl_delay,
        "user_agents": user_agents,
        "issues": issues,
    }


def _parse_sitemap_xml(content: str, sitemap_url: str, max_urls: int = 50000) -> dict:
    """Parse sitemap XML content, handles both sitemapindex and urlset."""
    urls = []
    child_sitemaps = []
    sitemap_type = "unknown"
    issues = []

    try:
        root = ET.fromstring(content)
        # Strip namespace
        tag = root.tag
        if "}" in tag:
            tag = tag.split("}", 1)[1]

        if tag == "sitemapindex":
            sitemap_type = "index"
            ns = ""
            if "{" in root.tag:
                ns = root.tag.split("}")[0] + "}"
            for sitemap_el in root.findall("{}sitemap".format(ns)):
                loc = sitemap_el.find("{}loc".format(ns))
                if loc is not None and loc.text:
                    child_sitemaps.append(loc.text.strip())

        elif tag == "urlset":
            sitemap_type = "urlset"
            ns = ""
            if "{" in root.tag:
                ns = root.tag.split("}")[0] + "}"
            has_lastmod = False
            has_changefreq = False
            for url_el in root.findall("{}url".format(ns)):
                loc = url_el.find("{}loc".format(ns))
                if loc is not None and loc.text:
                    urls.append(loc.text.strip())
                lastmod = url_el.find("{}lastmod".format(ns))
                if lastmod is not None and lastmod.text:
                    has_lastmod = True
                changefreq = url_el.find("{}changefreq".format(ns))
                if changefreq is not None and changefreq.text:
                    has_changefreq = True

            if not has_lastmod:
                issues.append(_make_issue(
                    "info",
                    "sitemap_no_lastmod",
                    "Sitemap enthält keine lastmod-Angaben.",
                    "Füge lastmod-Tags hinzu, damit Suchmaschinen Änderungen besser erkennen."
                ))
            if not has_changefreq:
                issues.append(_make_issue(
                    "info",
                    "sitemap_no_changefreq",
                    "Sitemap enthält keine changefreq-Angaben.",
                    "Füge changefreq-Tags hinzu als Crawl-Hinweis."
                ))

            if len(urls) > max_urls:
                issues.append(_make_issue(
                    "warning",
                    "sitemap_too_large",
                    "Sitemap enthält {} URLs (Limit: {}).".format(len(urls), max_urls),
                    "Teile die Sitemap in mehrere Dateien auf und verwende einen Sitemap-Index."
                ))

    except ET.ParseError as e:
        issues.append(_make_issue(
            "critical",
            "sitemap_parse_error",
            "Sitemap XML konnte nicht geparst werden: {}".format(str(e)),
            "Stelle sicher, dass die Sitemap valides XML ist."
        ))

    return {
        "type": sitemap_type,
        "urls": urls[:max_urls],
        "child_sitemaps": child_sitemaps,
        "issues": issues,
    }


def analyze_sitemap(sitemap_url: str, max_urls: int = 50000) -> dict:
    """
    Loads and analyzes sitemap.xml (including Sitemap Index).
    Returns dict with found, type, urls, child_sitemaps, total_url_count, issues.
    """
    issues = []
    all_urls = []
    child_sitemaps = []
    sitemap_type = "unknown"
    found = False

    urls_to_try = [sitemap_url]
    # If the URL looks like a base URL, try common sitemap paths
    parsed = urlparse(sitemap_url)
    if not parsed.path or parsed.path == "/":
        urls_to_try = [
            urljoin(sitemap_url, "/sitemap.xml"),
            urljoin(sitemap_url, "/sitemap_index.xml"),
        ]

    fetched_url = None
    content = None

    for try_url in urls_to_try:
        try:
            resp = requests.get(try_url, timeout=DEFAULT_TIMEOUT, headers=HEADERS, allow_redirects=True)
            if resp.status_code == 200:
                found = True
                content = resp.text
                fetched_url = try_url
                break
        except requests.RequestException:
            continue

    if not found:
        issues.append(_make_issue(
            "warning",
            "sitemap_not_found",
            "Sitemap konnte nicht gefunden werden. Versucht: {}".format(", ".join(urls_to_try)),
            "Erstelle eine sitemap.xml und verlinke sie in robots.txt."
        ))
        return {
            "found": False,
            "url": urls_to_try[0] if urls_to_try else sitemap_url,
            "type": "unknown",
            "urls": [],
            "child_sitemaps": [],
            "total_url_count": 0,
            "issues": issues,
        }

    parsed_data = _parse_sitemap_xml(content, fetched_url, max_urls)
    sitemap_type = parsed_data["type"]
    all_urls = parsed_data["urls"]
    child_sitemaps = parsed_data["child_sitemaps"]
    issues.extend(parsed_data["issues"])

    # For sitemap index: fetch child sitemaps and aggregate URLs
    if sitemap_type == "index" and child_sitemaps:
        for child_url in child_sitemaps[:10]:  # limit to 10 child sitemaps
            try:
                child_resp = requests.get(child_url, timeout=DEFAULT_TIMEOUT, headers=HEADERS, allow_redirects=True)
                if child_resp.status_code == 200:
                    child_data = _parse_sitemap_xml(child_resp.text, child_url, max_urls)
                    all_urls.extend(child_data["urls"])
                    issues.extend(child_data["issues"])
                    if len(all_urls) >= max_urls:
                        all_urls = all_urls[:max_urls]
                        break
            except requests.RequestException as e:
                issues.append(_make_issue(
                    "warning",
                    "sitemap_child_fetch_error",
                    "Child-Sitemap konnte nicht geladen werden: {}".format(child_url),
                    "Überprüfe die Erreichbarkeit der Kind-Sitemap."
                ))

    return {
        "found": True,
        "url": fetched_url,
        "type": sitemap_type,
        "urls": all_urls,
        "child_sitemaps": child_sitemaps,
        "total_url_count": len(all_urls),
        "issues": issues,
    }
