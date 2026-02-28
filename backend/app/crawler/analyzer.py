from typing import List, Dict, Any
import re
from collections import Counter
from urllib.parse import urlparse


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
    THIN_CONTENT_WORDS = 300
    SLOW_RESPONSE_SEC = 3.0
    URL_MAX_LENGTH = 100
    STOPWORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "can", "not", "this",
        "that", "these", "those", "it", "its", "as", "if", "then", "than",
        "so", "up", "out", "about", "into", "through", "during", "before",
        "after", "above", "below", "between", "each", "more", "most", "other",
        "some", "such", "no", "nor", "only", "same", "too", "very", "just",
        "also", "we", "you", "he", "she", "they", "i", "my", "your", "his",
        "her", "our", "their", "what", "which", "who", "whom", "how", "when",
        "where", "why", "all", "any", "both", "few", "own", "over", "under",
    }

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
                "Add a unique, descriptive title tag (30-60 characters) to every page."))
        elif len(title) < self.TITLE_MIN:
            issues.append(SEOIssue("warning", "title_too_short",
                f"Title too short: {len(title)} chars (min {self.TITLE_MIN}): '{title[:80]}'",
                f"Expand the title to at least {self.TITLE_MIN} characters."))
        elif len(title) > self.TITLE_MAX:
            issues.append(SEOIssue("warning", "title_too_long",
                f"Title too long: {len(title)} chars (max {self.TITLE_MAX}): '{title[:80]}..'",
                f"Shorten the title to max {self.TITLE_MAX} characters to avoid SERP truncation."))

        # Meta description
        meta = (page.get("meta_description") or "").strip()
        if not meta:
            issues.append(SEOIssue("warning", "missing_meta_description",
                "Page is missing a meta description",
                "Add a compelling meta description (70-160 characters) to improve CTR."))
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

        # Images without alt (enhanced)
        imgs_no_alt = page.get("images_without_alt", 0)
        total_imgs = page.get("extra_data", {}) and page.get("extra_data", {}).get("total_images", 0) or 0
        if imgs_no_alt > 0:
            detail = f" ({imgs_no_alt}/{total_imgs} images)" if total_imgs > 0 else f" ({imgs_no_alt} image(s))"
            issues.append(SEOIssue("warning", "images_missing_alt",
                f"{imgs_no_alt} image(s) missing alt text{detail}",
                "Add descriptive alt text to all images for accessibility and image SEO."))

        # Word count / thin content (enhanced)
        words = page.get("word_count", 0)
        if 0 < words < 100:
            issues.append(SEOIssue("info", "low_word_count",
                f"Thin content: only {words} words on page",
                "Consider adding more quality content. Thin pages may rank poorly."))
        elif 100 <= words < self.THIN_CONTENT_WORDS:
            issues.append(SEOIssue("warning", "thin_content",
                f"Thin content warning: only {words} words (recommended: {self.THIN_CONTENT_WORDS}+)",
                f"Expand content to at least {self.THIN_CONTENT_WORDS} words for better rankings."))

        # Slow response
        rt = page.get("response_time", 0) or 0
        if rt > self.SLOW_RESPONSE_SEC:
            issues.append(SEOIssue("warning", "slow_response",
                f"Slow response time: {rt:.2f}s (threshold: {self.SLOW_RESPONSE_SEC}s)",
                "Optimize server response time. Page speed is a Google ranking factor."))

        # Canonical mismatch
        canonical = page.get("canonical_url")
        url = page.get("url", "")
        if canonical and canonical != url:
            issues.append(SEOIssue("info", "canonical_mismatch",
                f"Canonical URL differs from page URL: {canonical}",
                "Verify this canonical is intentional. Non-canonical pages won't rank."))

        # URL checks
        if url:
            parsed_url = urlparse(url)
            path = parsed_url.path

            if len(url) > self.URL_MAX_LENGTH:
                issues.append(SEOIssue("warning", "url_too_long",
                    f"URL too long: {len(url)} characters (max recommended: {self.URL_MAX_LENGTH})",
                    "Use shorter, descriptive URLs. Long URLs may be truncated in SERPs."))

            if re.search(r"[A-Z]", path):
                issues.append(SEOIssue("warning", "url_has_uppercase",
                    f"URL path contains uppercase letters: {path[:100]}",
                    "Use lowercase letters in URLs to avoid duplicate content issues."))

            if " " in url or "%20" in url:
                issues.append(SEOIssue("warning", "url_has_spaces",
                    "URL contains spaces or encoded spaces (%20)",
                    "Replace spaces with hyphens in URL slugs."))

            depth_slashes = path.rstrip("/").count("/")
            if depth_slashes >= 5:
                issues.append(SEOIssue("info", "deep_url",
                    f"URL is deeply nested ({depth_slashes} levels deep): {path[:100]}",
                    "Keep important pages within 3-4 clicks from the homepage for better crawlability."))

        # Noindex detection
        is_indexable = page.get("is_indexable", True)
        if not is_indexable:
            issues.append(SEOIssue("warning", "noindex",
                "Page has noindex directive — will be excluded from search engines",
                "Verify this noindex is intentional. Remove it if the page should be indexed."))

        # extra_data based checks (from spider)
        extra = page.get("extra_data") or {}

        # Open Graph checks
        if not extra.get("og_title"):
            issues.append(SEOIssue("warning", "missing_og_title",
                "Missing Open Graph og:title tag",
                "Add og:title for better social media sharing appearance."))
        if not extra.get("og_description"):
            issues.append(SEOIssue("warning", "missing_og_description",
                "Missing Open Graph og:description tag",
                "Add og:description to control how the page appears when shared on social media."))
        if not extra.get("og_image"):
            issues.append(SEOIssue("warning", "missing_og_image",
                "Missing Open Graph og:image tag",
                "Add og:image (min 1200x630px) for rich social media previews."))

        # Twitter Card
        if not extra.get("twitter_card"):
            issues.append(SEOIssue("info", "missing_twitter_card",
                "Missing Twitter Card (twitter:card) meta tag",
                "Add twitter:card meta tag to control how your page appears in Twitter/X posts."))

        # Schema.org / JSON-LD
        if not extra.get("has_jsonld") and not extra.get("has_schema_org"):
            issues.append(SEOIssue("info", "missing_structured_data",
                "No Schema.org / JSON-LD structured data found",
                "Add structured data (JSON-LD) to enable rich results in Google Search."))

        # Keyword density
        body_text = extra.get("body_text", "")
        if body_text and words >= 100:
            top_keywords = self._calculate_keyword_density(body_text, top_n=5)
            if top_keywords:
                kw_str = ", ".join(f"{kw} ({count}x)" for kw, count in top_keywords)
                issues.append(SEOIssue("info", "keyword_density",
                    f"Top keywords: {kw_str}",
                    "Ensure your target keyword appears naturally in title, H1, and body content."))

        # Nofollow links
        nofollow_count = extra.get("nofollow_links_count", 0)
        if nofollow_count and nofollow_count > 0:
            issues.append(SEOIssue("info", "nofollow_links",
                f"Page contains {nofollow_count} nofollow link(s)",
                "Review nofollow links. Excessive nofollow usage can limit PageRank flow."))

        # Internal links
        int_links = page.get("internal_links_count", 0)
        ext_links = page.get("external_links_count", 0)
        if int_links == 0 and status == 200:
            issues.append(SEOIssue("info", "no_internal_links",
                "Page has no internal links",
                "Add internal links to improve site navigation and distribute PageRank."))
        if ext_links > 100:
            issues.append(SEOIssue("info", "many_external_links",
                f"Page has {ext_links} external links — unusually high",
                "Review external links. Too many outbound links can dilute PageRank."))

        return issues

    def _calculate_keyword_density(self, text: str, top_n: int = 5) -> List[tuple]:
        """Calculate top N keywords by frequency, excluding stopwords."""
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        filtered = [w for w in words if w not in self.STOPWORDS]
        if not filtered:
            return []
        counter = Counter(filtered)
        return counter.most_common(top_n)
