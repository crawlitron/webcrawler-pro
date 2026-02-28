
from typing import List, Dict, Any


class SEOIssue:
    def __init__(self, severity: str, issue_type: str, description: str, recommendation: str = ""):
        self.severity = severity
        self.issue_type = issue_type
        self.description = description
        self.recommendation = recommendation


class SEOAnalyzer:
    TITLE_MIN = 30
    TITLE_MAX = 60
    META_MIN = 70
    META_MAX = 160

    def analyze(self, page: Dict[str, Any]) -> List[SEOIssue]:
        issues = []
        status = page.get("status_code")
        ct = page.get("content_type", "") or ""

        if ct and "text/html" not in ct:
            return issues

        # Status code issues
        if status:
            if status >= 500:
                issues.append(SEOIssue("critical", "server_error",
                    f"Server error: HTTP {status}",
                    "Fix server errors immediately — these pages are not crawlable by search engines."))
            elif status >= 400:
                issues.append(SEOIssue("critical", "client_error",
                    f"Client error: HTTP {status} — page not found or inaccessible",
                    "Fix or redirect broken URLs. These pages waste crawl budget."))
            elif status in (301, 302, 307, 308):
                redir = page.get("redirect_url", "unknown")
                issues.append(SEOIssue("warning", "redirect",
                    f"Page redirects ({status}) to: {redir}",
                    "Ensure redirects point directly to the final URL. Avoid redirect chains."))

        if status != 200:
            return issues

        # Title
        title = (page.get("title") or "").strip()
        if not title:
            issues.append(SEOIssue("critical", "missing_title",
                "Page is missing a title tag",
                "Add a unique, descriptive title tag (30–60 characters) to every page."))
        elif len(title) < self.TITLE_MIN:
            issues.append(SEOIssue("warning", "title_too_short",
                f"Title too short: {len(title)} chars (min {self.TITLE_MIN}): '{title[:80]}'",
                f"Expand the title to at least {self.TITLE_MIN} characters."))
        elif len(title) > self.TITLE_MAX:
            issues.append(SEOIssue("warning", "title_too_long",
                f"Title too long: {len(title)} chars (max {self.TITLE_MAX}): '{title[:80]}…'",
                f"Shorten the title to max {self.TITLE_MAX} characters to avoid SERP truncation."))

        # Meta description
        meta = (page.get("meta_description") or "").strip()
        if not meta:
            issues.append(SEOIssue("warning", "missing_meta_description",
                "Page is missing a meta description",
                "Add a compelling meta description (70–160 characters) to improve CTR."))
        elif len(meta) < self.META_MIN:
            issues.append(SEOIssue("warning", "meta_description_too_short",
                f"Meta description too short: {len(meta)} chars (min {self.META_MIN})",
                f"Expand to at least {self.META_MIN} characters."))
        elif len(meta) > self.META_MAX:
            issues.append(SEOIssue("warning", "meta_description_too_long",
                f"Meta description too long: {len(meta)} chars (max {self.META_MAX})",
                f"Shorten to max {self.META_MAX} characters."))

        # H1
        h1 = (page.get("h1") or "").strip()
        h1_count = page.get("h1_count", 0)
        if not h1:
            issues.append(SEOIssue("critical", "missing_h1",
                "Page is missing an H1 heading",
                "Add exactly one H1 heading describing the main topic of the page."))
        elif h1_count > 1:
            issues.append(SEOIssue("warning", "multiple_h1",
                f"Page has {h1_count} H1 headings (should have exactly 1)",
                "Use only one H1 per page. Convert extra H1s to H2 or H3."))

        # Images without alt
        imgs = page.get("images_without_alt", 0)
        if imgs > 0:
            issues.append(SEOIssue("warning", "images_missing_alt",
                f"{imgs} image(s) missing alt text",
                "Add descriptive alt text to all images for accessibility and image SEO."))

        # Low word count
        words = page.get("word_count", 0)
        if 0 < words < 100:
            issues.append(SEOIssue("info", "low_word_count",
                f"Thin content: only {words} words on page",
                "Consider adding more quality content. Thin pages may rank poorly."))

        # Slow response
        rt = page.get("response_time", 0) or 0
        if rt > 3.0:
            issues.append(SEOIssue("warning", "slow_response",
                f"Slow response time: {rt:.2f}s (threshold: 3s)",
                "Optimize server response time. Page speed is a Google ranking factor."))

        # Canonical mismatch
        canonical = page.get("canonical_url")
        url = page.get("url", "")
        if canonical and canonical != url:
            issues.append(SEOIssue("info", "canonical_mismatch",
                f"Canonical URL differs from page URL: {canonical}",
                "Verify this canonical is intentional. Non-canonical pages won't rank."))

        return issues
