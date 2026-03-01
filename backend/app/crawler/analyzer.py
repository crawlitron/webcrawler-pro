from typing import List, Dict, Any, Optional
import re
from collections import Counter, defaultdict
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
    IMAGE_SIZE_THRESHOLD_KB = 200
    IMAGE_ALT_MAX_LENGTH = 100
    REDIRECT_CHAIN_MAX_HOPS = 2
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

    # ------------------------------------------------------------------
    # Main per-page analysis (unchanged + image/redirect calls integrated)
    # ------------------------------------------------------------------
    def analyze(self, page: Dict[str, Any]) -> List[SEOIssue]:
        issues = []
        status = page.get("status_code")
        ct = page.get("content_type", "") or ""

        if ct and "text/html" not in ct:
            return issues

        # Status code issues
        if status:
            if status >= 500:
                issues.append(SEOIssue(
                    "critical", "server_error",
                    "Server error: HTTP {}".format(status),
                    "Fix server errors immediately — these pages are not crawlable by search engines."))
            elif status >= 400:
                issues.append(SEOIssue(
                    "critical", "client_error",
                    "Client error: HTTP {} — page not found or inaccessible".format(status),
                    "Fix or redirect broken URLs. These pages waste crawl budget."))
            elif status in (301, 302, 307, 308):
                redir = page.get("redirect_url", "unknown")
                issues.append(SEOIssue(
                    "warning", "redirect",
                    "Page redirects ({}) to: {}".format(status, redir),
                    "Ensure redirects point directly to the final URL. Avoid redirect chains."))

        if status != 200:
            return issues

        # Title
        title = (page.get("title") or "").strip()
        if not title:
            issues.append(SEOIssue(
                "critical", "missing_title",
                "Page is missing a title tag",
                "Add a unique, descriptive title tag (30-60 characters) to every page."))
        elif len(title) < self.TITLE_MIN:
            issues.append(SEOIssue(
                "warning", "title_too_short",
                "Title too short: {} chars (min {}): '{}'".format(len(title), self.TITLE_MIN, title[:80]),
                "Expand the title to at least {} characters.".format(self.TITLE_MIN)))
        elif len(title) > self.TITLE_MAX:
            issues.append(SEOIssue(
                "warning", "title_too_long",
                "Title too long: {} chars (max {}): '{}'..".format(len(title), self.TITLE_MAX, title[:80]),
                "Shorten the title to max {} characters to avoid SERP truncation.".format(self.TITLE_MAX)))

        # Meta description
        meta = (page.get("meta_description") or "").strip()
        if not meta:
            issues.append(SEOIssue(
                "warning", "missing_meta_description",
                "Page is missing a meta description",
                "Add a compelling meta description (70-160 characters) to improve CTR."))
        elif len(meta) < self.META_MIN:
            issues.append(SEOIssue(
                "warning", "meta_description_too_short",
                "Meta description too short: {} chars (min {})".format(len(meta), self.META_MIN),
                "Expand to at least {} characters.".format(self.META_MIN)))
        elif len(meta) > self.META_MAX:
            issues.append(SEOIssue(
                "warning", "meta_description_too_long",
                "Meta description too long: {} chars (max {})".format(len(meta), self.META_MAX),
                "Shorten to max {} characters.".format(self.META_MAX)))

        # H1
        h1 = (page.get("h1") or "").strip()
        h1_count = page.get("h1_count", 0)
        if not h1:
            issues.append(SEOIssue(
                "critical", "missing_h1",
                "Page is missing an H1 heading",
                "Add exactly one H1 heading describing the main topic of the page."))
        elif h1_count > 1:
            issues.append(SEOIssue(
                "warning", "multiple_h1",
                "Page has {} H1 headings (should have exactly 1)".format(h1_count),
                "Use only one H1 per page. Convert extra H1s to H2 or H3."))

        # Images without alt (summary - detailed per-image issues from analyze_images)
        imgs_no_alt = page.get("images_without_alt", 0)
        extra = page.get("extra_data") or {}
        total_imgs = extra.get("total_images", 0) or 0
        if imgs_no_alt > 0:
            detail = " ({}/{} images)".format(imgs_no_alt, total_imgs) if total_imgs > 0 else " ({} image(s))".format(imgs_no_alt)
            issues.append(SEOIssue(
                "warning", "images_missing_alt",
                "{} image(s) missing alt text{}".format(imgs_no_alt, detail),
                "Add descriptive alt text to all images for accessibility and image SEO."))

        # Word count / thin content
        words = page.get("word_count", 0)
        if 0 < words < 100:
            issues.append(SEOIssue(
                "info", "low_word_count",
                "Thin content: only {} words on page".format(words),
                "Consider adding more quality content. Thin pages may rank poorly."))
        elif 100 <= words < self.THIN_CONTENT_WORDS:
            issues.append(SEOIssue(
                "warning", "thin_content",
                "Thin content warning: only {} words (recommended: {}+)".format(words, self.THIN_CONTENT_WORDS),
                "Expand content to at least {} words for better rankings.".format(self.THIN_CONTENT_WORDS)))

        # Slow response
        rt = page.get("response_time", 0) or 0
        if rt > self.SLOW_RESPONSE_SEC:
            issues.append(SEOIssue(
                "warning", "slow_response",
                "Slow response time: {:.2f}s (threshold: {}s)".format(rt, self.SLOW_RESPONSE_SEC),
                "Optimize server response time. Page speed is a Google ranking factor."))

        # Canonical mismatch
        canonical = page.get("canonical_url")
        url = page.get("url", "")
        if canonical and canonical != url:
            issues.append(SEOIssue(
                "info", "canonical_mismatch",
                "Canonical URL differs from page URL: {}".format(canonical),
                "Verify this canonical is intentional. Non-canonical pages won't rank."))

        # URL checks
        if url:
            parsed_url = urlparse(url)
            path = parsed_url.path
            if len(url) > self.URL_MAX_LENGTH:
                issues.append(SEOIssue(
                    "warning", "url_too_long",
                    "URL too long: {} characters (max recommended: {})".format(len(url), self.URL_MAX_LENGTH),
                    "Use shorter, descriptive URLs. Long URLs may be truncated in SERPs."))
            if re.search(r"[A-Z]", path):
                issues.append(SEOIssue(
                    "warning", "url_has_uppercase",
                    "URL path contains uppercase letters: {}".format(path[:100]),
                    "Use lowercase letters in URLs to avoid duplicate content issues."))
            if " " in url or "%20" in url:
                issues.append(SEOIssue(
                    "warning", "url_has_spaces",
                    "URL contains spaces or encoded spaces (%20)",
                    "Replace spaces with hyphens in URL slugs."))
            depth_slashes = path.rstrip("/").count("/")
            if depth_slashes >= 5:
                issues.append(SEOIssue(
                    "info", "deep_url",
                    "URL is deeply nested ({} levels deep): {}".format(depth_slashes, path[:100]),
                    "Keep important pages within 3-4 clicks from the homepage for better crawlability."))

        # Noindex
        is_indexable = page.get("is_indexable", True)
        if not is_indexable:
            issues.append(SEOIssue(
                "warning", "noindex",
                "Page has noindex directive — will be excluded from search engines",
                "Verify this noindex is intentional. Remove it if the page should be indexed."))

        # Open Graph checks
        if not extra.get("og_title"):
            issues.append(SEOIssue(
                "warning", "missing_og_title",
                "Missing Open Graph og:title tag",
                "Add og:title for better social media sharing appearance."))
        if not extra.get("og_description"):
            issues.append(SEOIssue(
                "warning", "missing_og_description",
                "Missing Open Graph og:description tag",
                "Add og:description to control how the page appears when shared on social media."))
        if not extra.get("og_image"):
            issues.append(SEOIssue(
                "warning", "missing_og_image",
                "Missing Open Graph og:image tag",
                "Add og:image (min 1200x630px) for rich social media previews."))

        # Twitter Card
        if not extra.get("twitter_card"):
            issues.append(SEOIssue(
                "info", "missing_twitter_card",
                "Missing Twitter Card (twitter:card) meta tag",
                "Add twitter:card meta tag to control how your page appears in Twitter/X posts."))

        # Schema.org / JSON-LD
        if not extra.get("has_jsonld") and not extra.get("has_schema_org"):
            issues.append(SEOIssue(
                "info", "missing_structured_data",
                "No Schema.org / JSON-LD structured data found",
                "Add structured data (JSON-LD) to enable rich results in Google Search."))

        # Keyword density
        body_text = extra.get("body_text", "")
        if body_text and words >= 100:
            top_keywords = self._calculate_keyword_density(body_text, top_n=5)
            if top_keywords:
                kw_str = ", ".join("{} ({}x)".format(kw, count) for kw, count in top_keywords)
                issues.append(SEOIssue(
                    "info", "keyword_density",
                    "Top keywords: {}".format(kw_str),
                    "Ensure your target keyword appears naturally in title, H1, and body content."))

        # Nofollow links
        nofollow_count = extra.get("nofollow_links_count", 0)
        if nofollow_count and nofollow_count > 0:
            issues.append(SEOIssue(
                "info", "nofollow_links",
                "Page contains {} nofollow link(s)".format(nofollow_count),
                "Review nofollow links. Excessive nofollow usage can limit PageRank flow."))

        # Internal links
        int_links = page.get("internal_links_count", 0)
        ext_links = page.get("external_links_count", 0)
        if int_links == 0 and status == 200:
            issues.append(SEOIssue(
                "info", "no_internal_links",
                "Page has no internal links",
                "Add internal links to improve site navigation and distribute PageRank."))
        if ext_links > 100:
            issues.append(SEOIssue(
                "info", "many_external_links",
                "Page has {} external links — unusually high".format(ext_links),
                "Review external links. Too many outbound links can dilute PageRank."))

        # --- Image SEO (detailed per-image checks) ---
        issues.extend(self.analyze_images(page))

        # --- Redirect chain checks ---
        issues.extend(self.analyze_redirects(page))

        return issues

    # ------------------------------------------------------------------
    # Feature 1: Image SEO Analysis
    # ------------------------------------------------------------------
    def analyze_images(self, page: Dict[str, Any]) -> List[SEOIssue]:
        """Detailed per-image SEO checks."""
        issues = []
        extra = page.get("extra_data") or {}
        images = extra.get("images", [])
        if not images:
            return issues

        missing_alt_urls = []
        empty_alt_urls = []
        long_alt_urls = []
        no_dims_urls = []
        broken_urls = []

        for img in images:
            src = img.get("src", "") or ""
            alt = img.get("alt", None)
            display_src = src[-60:] if len(src) > 60 else src

            # Missing alt attribute entirely
            if alt is None:
                missing_alt_urls.append(display_src)
            # Empty alt (attribute exists but blank)
            elif img.get("alt_empty"):
                empty_alt_urls.append(display_src)
            # Alt text too long
            elif img.get("alt_too_long"):
                long_alt_urls.append(display_src)

            # Missing width or height
            if img.get("missing_dimensions"):
                no_dims_urls.append(display_src)

            # Broken image (status checked in tasks.py via HEAD request)
            img_status = img.get("status_code")
            if img_status is not None and img_status not in (200, 304):
                broken_urls.append((display_src, img_status))

            # Large image
            size_bytes = img.get("size_bytes")
            if size_bytes and size_bytes > self.IMAGE_SIZE_THRESHOLD_KB * 1024:
                size_kb = size_bytes // 1024
                issues.append(SEOIssue(
                    "warning", "image_too_large",
                    "Large image ({}KB > {}KB): {}".format(size_kb, self.IMAGE_SIZE_THRESHOLD_KB, display_src),
                    "Compress images to under {}KB to improve page load speed.".format(self.IMAGE_SIZE_THRESHOLD_KB)))

        if missing_alt_urls:
            count = len(missing_alt_urls)
            issues.append(SEOIssue(
                "warning", "image_missing_alt",
                "{} image(s) missing alt attribute entirely".format(count),
                "Add descriptive alt text to all content images. Use alt=\"\" only for decorative images."))

        if empty_alt_urls:
            count = len(empty_alt_urls)
            issues.append(SEOIssue(
                "info", "image_empty_alt",
                "{} image(s) have empty alt attribute".format(count),
                "If these are content images, add descriptive alt text. Empty alt is correct only for decorative images."))

        if long_alt_urls:
            count = len(long_alt_urls)
            issues.append(SEOIssue(
                "info", "image_alt_too_long",
                "{} image(s) have alt text longer than {} characters".format(count, self.IMAGE_ALT_MAX_LENGTH),
                "Keep alt text concise (under {} chars). Use the title attribute for longer descriptions.".format(
                    self.IMAGE_ALT_MAX_LENGTH)))

        if no_dims_urls:
            count = len(no_dims_urls)
            issues.append(SEOIssue(
                "info", "image_no_dimensions",
                "{} image(s) missing width/height attributes".format(count),
                "Add explicit width and height to all img tags to prevent layout shift (CLS)."))

        for src, st in broken_urls:
            issues.append(SEOIssue(
                "critical", "image_broken",
                "Broken image (HTTP {}): {}".format(st, src),
                "Fix or remove broken image references. They degrade user experience and may hurt SEO."))

        return issues

    # ------------------------------------------------------------------
    # Feature 2: Redirect Chain Analysis
    # ------------------------------------------------------------------
    def analyze_redirects(self, page: Dict[str, Any]) -> List[SEOIssue]:
        """Analyze redirect chains for loops and excessive hops."""
        issues = []
        extra = page.get("extra_data") or {}
        chain = extra.get("redirect_chain", [])
        hops = extra.get("redirect_hops", 0)

        if not chain or hops == 0:
            return issues

        # Detect redirect loop (URL appears more than once)
        seen_urls = set()
        loop_detected = False
        for hop in chain:
            hop_url = hop.get("url", "")
            if hop_url in seen_urls:
                loop_detected = True
                break
            seen_urls.add(hop_url)

        if loop_detected:
            issues.append(SEOIssue(
                "critical", "redirect_loop",
                "Redirect loop detected: URL appears multiple times in the redirect chain",
                "Fix the redirect configuration to eliminate circular redirects immediately."))
        elif hops > self.REDIRECT_CHAIN_MAX_HOPS:
            issues.append(SEOIssue(
                "warning", "redirect_chain_too_long",
                "Redirect chain too long: {} hops (max recommended: {})".format(hops, self.REDIRECT_CHAIN_MAX_HOPS),
                "Shorten redirect chains to a single redirect. Each hop adds latency and dilutes PageRank."))

        return issues

    # ------------------------------------------------------------------
    # Feature 3: Duplicate Content Detection (cross-page, post-crawl)
    # ------------------------------------------------------------------
    def analyze_duplicates(self, crawl_id: int, db) -> int:
        """Detect duplicate titles, meta descriptions, and H1s across all crawled pages.
        Creates Issue records directly in DB. Returns total duplicate issues created."""
        from app.models import Page, Issue, IssueSeverity

        pages = db.query(Page).filter(
            Page.crawl_id == crawl_id,
            Page.status_code == 200,
        ).all()

        total_created = 0

        # Group pages by title, meta_description, h1
        title_map = defaultdict(list)
        meta_map = defaultdict(list)
        h1_map = defaultdict(list)

        for page in pages:
            if page.title and page.title.strip():
                title_map[page.title.strip().lower()].append(page)
            if page.meta_description and page.meta_description.strip():
                meta_map[page.meta_description.strip().lower()].append(page)
            if page.h1 and page.h1.strip():
                h1_map[page.h1.strip().lower()].append(page)

        # Duplicate titles
        for title_val, dup_pages in title_map.items():
            if len(dup_pages) < 2:
                continue
            display_title = title_val[:60]
            urls_list = ", ".join(p.url for p in dup_pages[:3])
            extra_count = len(dup_pages) - 3
            if extra_count > 0:
                urls_list += " (+{} more)".format(extra_count)
            for p in dup_pages:
                issue = Issue(
                    crawl_id=crawl_id,
                    page_id=p.id,
                    severity=IssueSeverity.WARNING,
                    issue_type="duplicate_title",
                    description="Duplicate title '{}' shared by {} pages: {}".format(
                        display_title, len(dup_pages), urls_list),
                    recommendation="Each page should have a unique, descriptive title tag.",
                )
                db.add(issue)
                total_created += 1

        # Duplicate meta descriptions
        for meta_val, dup_pages in meta_map.items():
            if len(dup_pages) < 2:
                continue
            display_meta = meta_val[:60]
            urls_list = ", ".join(p.url for p in dup_pages[:3])
            extra_count = len(dup_pages) - 3
            if extra_count > 0:
                urls_list += " (+{} more)".format(extra_count)
            for p in dup_pages:
                issue = Issue(
                    crawl_id=crawl_id,
                    page_id=p.id,
                    severity=IssueSeverity.WARNING,
                    issue_type="duplicate_meta_description",
                    description="Duplicate meta description '{}' shared by {} pages: {}".format(
                        display_meta, len(dup_pages), urls_list),
                    recommendation="Write unique meta descriptions for each page to improve CTR in SERPs.",
                )
                db.add(issue)
                total_created += 1

        # Duplicate H1s
        for h1_val, dup_pages in h1_map.items():
            if len(dup_pages) < 2:
                continue
            display_h1 = h1_val[:60]
            urls_list = ", ".join(p.url for p in dup_pages[:3])
            extra_count = len(dup_pages) - 3
            if extra_count > 0:
                urls_list += " (+{} more)".format(extra_count)
            for p in dup_pages:
                issue = Issue(
                    crawl_id=crawl_id,
                    page_id=p.id,
                    severity=IssueSeverity.WARNING,
                    issue_type="duplicate_h1",
                    description="Duplicate H1 '{}' shared by {} pages: {}".format(
                        display_h1, len(dup_pages), urls_list),
                    recommendation="Each page should have a unique H1 heading reflecting the page topic.",
                )
                db.add(issue)
                total_created += 1

        if total_created > 0:
            db.commit()

        return total_created

    def _calculate_keyword_density(self, text: str, top_n: int = 5) -> List[tuple]:
        """Calculate top N keywords by frequency, excluding stopwords."""
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        filtered = [w for w in words if w not in self.STOPWORDS]
        if not filtered:
            return []
        counter = Counter(filtered)
        return counter.most_common(top_n)
