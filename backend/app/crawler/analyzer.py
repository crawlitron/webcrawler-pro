from typing import List, Dict, Any, Optional
import re
from collections import Counter, defaultdict
from urllib.parse import urlparse


class SEOIssue:
    def __init__(
        self,
        severity: str,
        issue_type: str,
        description: str,
        recommendation: str = "",
        category: str = "seo",
    ):
        self.severity = severity
        self.issue_type = issue_type
        self.description = description
        self.recommendation = recommendation
        self.category = category


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
        # English
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
        # German
        "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer",
        "einem", "eines", "und", "oder", "aber", "nicht", "mit", "von", "zu",
        "bei", "auf", "aus", "als", "auch", "ist", "sind", "war", "hat",
        "haben", "wird", "werden", "fuer", "an", "im", "sich", "sie", "er",
        "es", "wir", "ihr", "ich", "du", "nach", "seit", "noch", "bis",
        "dann", "wenn", "dass", "wie", "was", "kann", "mehr", "nur", "schon",
        "alle", "hier", "jetzt", "immer", "sehr", "neu", "gut", "ohne",
        "zwischen", "unter", "ueber", "vor", "hinter", "neben", "durch",
    }

    # ------------------------------------------------------------------
    # Main per-page analysis
    # ------------------------------------------------------------------
    def analyze(self, page: Dict[str, Any]) -> List[SEOIssue]:
        issues = []
        status = page.get("status_code")
        ct = page.get("content_type", "") or ""

        if ct and "text/html" not in ct:
            return issues

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

        imgs_no_alt = page.get("images_without_alt", 0)
        extra = page.get("extra_data") or {}
        total_imgs = extra.get("total_images", 0) or 0
        if imgs_no_alt > 0:
            detail = " ({}/{} images)".format(imgs_no_alt, total_imgs) if total_imgs > 0 else " ({} image(s))".format(imgs_no_alt)
            issues.append(SEOIssue(
                "warning", "images_missing_alt",
                "{} image(s) missing alt text{}".format(imgs_no_alt, detail),
                "Add descriptive alt text to all images for accessibility and image SEO."))

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

        rt = page.get("response_time", 0) or 0
        if rt > self.SLOW_RESPONSE_SEC:
            issues.append(SEOIssue(
                "warning", "slow_response",
                "Slow response time: {:.2f}s (threshold: {}s)".format(rt, self.SLOW_RESPONSE_SEC),
                "Optimize server response time. Page speed is a Google ranking factor."))

        canonical = page.get("canonical_url")
        url = page.get("url", "")
        if canonical and canonical != url:
            issues.append(SEOIssue(
                "info", "canonical_mismatch",
                "Canonical URL differs from page URL: {}".format(canonical),
                "Verify this canonical is intentional. Non-canonical pages won't rank."))

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

        is_indexable = page.get("is_indexable", True)
        if not is_indexable:
            issues.append(SEOIssue(
                "warning", "noindex",
                "Page has noindex directive — will be excluded from search engines",
                "Verify this noindex is intentional. Remove it if the page should be indexed."))

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

        if not extra.get("twitter_card"):
            issues.append(SEOIssue(
                "info", "missing_twitter_card",
                "Missing Twitter Card (twitter:card) meta tag",
                "Add twitter:card meta tag to control how your page appears in Twitter/X posts."))

        if not extra.get("has_jsonld") and not extra.get("has_schema_org"):
            issues.append(SEOIssue(
                "info", "missing_structured_data",
                "No Schema.org / JSON-LD structured data found",
                "Add structured data (JSON-LD) to enable rich results in Google Search."))

        body_text = extra.get("body_text", "")
        if body_text and words >= 100:
            top_keywords = self._calculate_keyword_density(body_text, top_n=5)
            if top_keywords:
                kw_str = ", ".join("{} ({}x)".format(kw, count) for kw, count in top_keywords)
                issues.append(SEOIssue(
                    "info", "keyword_density",
                    "Top keywords: {}".format(kw_str),
                    "Ensure your target keyword appears naturally in title, H1, and body content."))

        nofollow_count = extra.get("nofollow_links_count", 0)
        if nofollow_count and nofollow_count > 0:
            issues.append(SEOIssue(
                "info", "nofollow_links",
                "Page contains {} nofollow link(s)".format(nofollow_count),
                "Review nofollow links. Excessive nofollow usage can limit PageRank flow."))

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

        issues.extend(self.analyze_images(page))
        issues.extend(self.analyze_redirects(page))

        return issues

    # ------------------------------------------------------------------
    # Feature 1: Image SEO Analysis
    # ------------------------------------------------------------------
    def analyze_images(self, page: Dict[str, Any]) -> List[SEOIssue]:
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

            if alt is None:
                missing_alt_urls.append(display_src)
            elif img.get("alt_empty"):
                empty_alt_urls.append(display_src)
            elif img.get("alt_too_long"):
                long_alt_urls.append(display_src)

            if img.get("missing_dimensions"):
                no_dims_urls.append(display_src)

            img_status = img.get("status_code")
            if img_status is not None and img_status not in (200, 304):
                broken_urls.append((display_src, img_status))

            size_bytes = img.get("size_bytes")
            if size_bytes and size_bytes > self.IMAGE_SIZE_THRESHOLD_KB * 1024:
                size_kb = size_bytes // 1024
                issues.append(SEOIssue(
                    "warning", "image_too_large",
                    "Large image ({}KB > {}KB): {}".format(size_kb, self.IMAGE_SIZE_THRESHOLD_KB, display_src),
                    "Compress images to under {}KB to improve page load speed.".format(self.IMAGE_SIZE_THRESHOLD_KB)))

        if missing_alt_urls:
            issues.append(SEOIssue(
                "warning", "image_missing_alt",
                "{} image(s) missing alt attribute entirely".format(len(missing_alt_urls)),
                "Add descriptive alt text to all content images. Use alt="" only for decorative images."))
        if empty_alt_urls:
            issues.append(SEOIssue(
                "info", "image_empty_alt",
                "{} image(s) have empty alt attribute".format(len(empty_alt_urls)),
                "If these are content images, add descriptive alt text."))
        if long_alt_urls:
            issues.append(SEOIssue(
                "info", "image_alt_too_long",
                "{} image(s) have alt text longer than {} characters".format(len(long_alt_urls), self.IMAGE_ALT_MAX_LENGTH),
                "Keep alt text concise (under {} chars).".format(self.IMAGE_ALT_MAX_LENGTH)))
        if no_dims_urls:
            issues.append(SEOIssue(
                "info", "image_no_dimensions",
                "{} image(s) missing width/height attributes".format(len(no_dims_urls)),
                "Add explicit width and height to all img tags to prevent layout shift (CLS)."))
        for src, st in broken_urls:
            issues.append(SEOIssue(
                "critical", "image_broken",
                "Broken image (HTTP {}): {}".format(st, src),
                "Fix or remove broken image references."))

        return issues

    # ------------------------------------------------------------------
    # Feature 2: Redirect Chain Analysis
    # ------------------------------------------------------------------
    def analyze_redirects(self, page: Dict[str, Any]) -> List[SEOIssue]:
        issues = []
        extra = page.get("extra_data") or {}
        chain = extra.get("redirect_chain", [])
        hops = extra.get("redirect_hops", 0)

        if not chain or hops == 0:
            return issues

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
                "Shorten redirect chains to a single redirect."))

        return issues

    # ------------------------------------------------------------------
    # Feature 3: Duplicate Content Detection
    # ------------------------------------------------------------------
    def analyze_duplicates(self, crawl_id: int, db) -> int:
        from app.models import Page, Issue, IssueSeverity

        pages = db.query(Page).filter(
            Page.crawl_id == crawl_id,
            Page.status_code == 200,
        ).all()

        total_created = 0
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
                    crawl_id=crawl_id, page_id=p.id,
                    severity=IssueSeverity.WARNING,
                    issue_type="duplicate_title",
                    description="Duplicate title '{}' shared by {} pages: {}".format(
                        display_title, len(dup_pages), urls_list),
                    recommendation="Each page should have a unique, descriptive title tag.",
                    category="seo",
                )
                db.add(issue)
                total_created += 1

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
                    crawl_id=crawl_id, page_id=p.id,
                    severity=IssueSeverity.WARNING,
                    issue_type="duplicate_meta_description",
                    description="Duplicate meta description '{}' shared by {} pages: {}".format(
                        display_meta, len(dup_pages), urls_list),
                    recommendation="Write unique meta descriptions for each page.",
                    category="seo",
                )
                db.add(issue)
                total_created += 1

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
                    crawl_id=crawl_id, page_id=p.id,
                    severity=IssueSeverity.WARNING,
                    issue_type="duplicate_h1",
                    description="Duplicate H1 '{}' shared by {} pages: {}".format(
                        display_h1, len(dup_pages), urls_list),
                    recommendation="Each page should have a unique H1 heading.",
                    category="seo",
                )
                db.add(issue)
                total_created += 1

        if total_created > 0:
            db.commit()

        return total_created

    # ------------------------------------------------------------------
    # Feature 4: Accessibility Analysis (BFSG/WCAG 2.1) - v0.5.0
    # ------------------------------------------------------------------
    def analyze_accessibility(self, page: Dict[str, Any]) -> List[SEOIssue]:
        """Analyze page for WCAG 2.1 Level A/AA and BFSG compliance.
        Uses pre-extracted a11y data from spider extra_data."""
        issues = []
        extra = page.get("extra_data") or {}
        a11y = extra.get("a11y") or {}

        if not a11y:
            return issues

        # === 1. PERCEIVABLE ===

        # WCAG 1.1.1 - Images without alt
        missing_alt = a11y.get("images_missing_alt", [])
        if missing_alt:
            count = len(missing_alt)
            issues.append(SEOIssue(
                "critical", "a11y_missing_alt_text",
                "WCAG 1.1.1: {} image(s) missing alt attribute".format(count),
                "Add descriptive alt text to all non-decorative images. Use alt="" for decorative images.",
                category="accessibility",
            ))

        # WCAG 1.1.1 - Non-decorative images with empty alt
        empty_alt_non_deco = a11y.get("images_empty_alt_non_decorative", [])
        if empty_alt_non_deco:
            count = len(empty_alt_non_deco)
            issues.append(SEOIssue(
                "warning", "a11y_empty_alt_non_decorative",
                "WCAG 1.1.1: {} non-decorative image(s) have empty alt attribute".format(count),
                "Add descriptive alt text to content images. Empty alt is only correct for purely decorative images.",
                category="accessibility",
            ))

        # WCAG 1.2.x - Video/Audio without captions
        media_no_captions = a11y.get("media_missing_captions", [])
        for media_item in media_no_captions:
            tag = media_item.get("tag", "media")
            issues.append(SEOIssue(
                "critical", "a11y_missing_captions",
                "WCAG 1.2.x: <{}> element missing captions/subtitles track".format(tag),
                "Add a <track kind='captions'> element to all video and audio elements.",
                category="accessibility",
            ))

        # WCAG 3.1.1 - lang attribute missing
        if a11y.get("html_lang_missing"):
            issues.append(SEOIssue(
                "critical", "a11y_missing_lang",
                "WCAG 3.1.1: <html> tag missing lang attribute",
                "Add lang='de' (or appropriate language code) to the <html> tag.",
                category="accessibility",
            ))
        elif a11y.get("html_lang_short"):
            issues.append(SEOIssue(
                "warning", "a11y_invalid_lang",
                "WCAG 3.1.1: <html> lang attribute appears invalid: '{}'".format(a11y.get("html_lang", "")),
                "Use a valid BCP 47 language tag (e.g., 'de', 'en', 'de-DE').",
                category="accessibility",
            ))

        # === 2. OPERABLE ===

        # WCAG 2.4.4 - Links without recognizable text
        vague_links = a11y.get("vague_links", [])
        if vague_links:
            count = len(vague_links)
            sample = vague_links[0].get("text", "") if vague_links else ""
            issues.append(SEOIssue(
                "warning", "a11y_vague_link_text",
                "WCAG 2.4.4: {} link(s) with vague text (e.g., '{}', 'mehr', 'click here')".format(count, sample),
                "Use descriptive link text that explains the destination or action.",
                category="accessibility",
            ))

        # WCAG 2.4.4 - Empty links
        empty_links = a11y.get("empty_links", [])
        if empty_links:
            count = len(empty_links)
            issues.append(SEOIssue(
                "critical", "a11y_empty_link",
                "WCAG 2.4.4: {} empty link(s) with no text or aria-label".format(count),
                "Add descriptive text or aria-label to all links.",
                category="accessibility",
            ))

        # WCAG 2.4.4 - Icon-only links without aria-label
        icon_links = a11y.get("icon_links_no_aria", [])
        if icon_links:
            count = len(icon_links)
            issues.append(SEOIssue(
                "warning", "a11y_icon_link_no_aria",
                "WCAG 2.4.4: {} icon-only link(s) missing aria-label".format(count),
                "Add aria-label to icon-only links to describe their purpose to screen reader users.",
                category="accessibility",
            ))

        # WCAG 2.4.1 - Skip navigation
        if not a11y.get("skip_nav_found"):
            issues.append(SEOIssue(
                "info", "a11y_missing_skip_nav",
                "WCAG 2.4.1: No skip navigation link found",
                "Add a 'Skip to main content' link as the first focusable element for keyboard users.",
                category="accessibility",
            ))

        # WCAG 2.4.3 - Positive tabindex
        pos_tabindex = a11y.get("positive_tabindex", [])
        if pos_tabindex:
            count = len(pos_tabindex)
            issues.append(SEOIssue(
                "warning", "a11y_positive_tabindex",
                "WCAG 2.4.3: {} element(s) use positive tabindex values (disrupts natural tab order)".format(count),
                "Remove positive tabindex values. Use tabindex='0' or -1 only.",
                category="accessibility",
            ))

        # === 3. UNDERSTANDABLE ===

        # WCAG 1.3.1 / 3.3.2 - Inputs without labels
        inputs_no_label = a11y.get("inputs_missing_label", [])
        if inputs_no_label:
            count = len(inputs_no_label)
            issues.append(SEOIssue(
                "critical", "a11y_input_missing_label",
                "WCAG 1.3.1/3.3.2: {} form input(s) missing associated label".format(count),
                "Add <label for='id'> or aria-label to every form input.",
                category="accessibility",
            ))

        # WCAG 4.1.2 - Buttons without accessible text
        buttons_no_label = a11y.get("buttons_missing_label", [])
        if buttons_no_label:
            count = len(buttons_no_label)
            issues.append(SEOIssue(
                "critical", "a11y_button_missing_label",
                "WCAG 4.1.2: {} button(s) missing accessible text or aria-label".format(count),
                "Add visible text or aria-label to all buttons.",
                category="accessibility",
            ))

        # WCAG 1.3.1 - Select without label
        selects_no_label = a11y.get("select_missing_label", [])
        if selects_no_label:
            count = len(selects_no_label)
            issues.append(SEOIssue(
                "warning", "a11y_select_missing_label",
                "WCAG 1.3.1: {} <select> element(s) missing associated label".format(count),
                "Add <label> or aria-label to all select elements.",
                category="accessibility",
            ))

        # === 4. ROBUST ===

        # WCAG 4.1.1 - Duplicate IDs
        dup_ids = a11y.get("duplicate_ids", [])
        if dup_ids:
            count = len(dup_ids)
            sample = ", ".join("#{}".format(i) for i in dup_ids[:3])
            issues.append(SEOIssue(
                "warning", "a11y_duplicate_ids",
                "WCAG 4.1.1: {} duplicate ID(s) found: {}".format(count, sample),
                "Ensure all HTML id attributes are unique on the page.",
                category="accessibility",
            ))

        # WCAG 2.4.2 - Title tag (cross-check with SEO title check, mark as a11y too)
        title = (page.get("title") or "").strip()
        if not title:
            issues.append(SEOIssue(
                "critical", "a11y_missing_title",
                "WCAG 2.4.2: Page missing <title> tag (required for accessibility)",
                "Add a descriptive <title> to every page.",
                category="accessibility",
            ))

        # WCAG 1.4.4 - Viewport scaling
        if a11y.get("viewport_no_scale"):
            issues.append(SEOIssue(
                "critical", "a11y_viewport_no_scale",
                "WCAG 1.4.4: viewport meta uses user-scalable=no (prevents zoom for low-vision users)",
                "Remove user-scalable=no from the viewport meta tag.",
                category="accessibility",
            ))

        max_scale = a11y.get("viewport_max_scale")
        if max_scale is not None and max_scale < 2.0:
            issues.append(SEOIssue(
                "warning", "a11y_viewport_limited_scale",
                "WCAG 1.4.4: viewport maximum-scale={} (should be >= 2 for accessibility)".format(max_scale),
                "Set maximum-scale to at least 2.0 or remove the restriction.",
                category="accessibility",
            ))

        # === 5. BFSG-specific checks ===

        if not a11y.get("has_contact_link"):
            issues.append(SEOIssue(
                "info", "bfsg_missing_contact",
                "BFSG: No contact information (tel: or mailto: link) found on page",
                "Add contact information (phone number or email) to comply with BFSG requirements.",
                category="accessibility",
            ))

        if not a11y.get("has_impressum_link"):
            issues.append(SEOIssue(
                "info", "bfsg_missing_impressum",
                "BFSG: No Impressum/Imprint link found on page",
                "Add a visible link to your Impressum page (legally required in Germany).",
                category="accessibility",
            ))

        if not a11y.get("has_accessibility_statement"):
            issues.append(SEOIssue(
                "info", "bfsg_missing_a11y_statement",
                "BFSG §12: No Accessibility Statement (Barrierefreiheitserklarung) link found",
                "Publish an accessibility statement and link to it from every page (required by BFSG from 28 June 2025).",
                category="accessibility",
            ))

        return issues

    # ------------------------------------------------------------------
    # Feature 5: Keyword Analysis - v0.5.0
    # ------------------------------------------------------------------
    def analyze_keywords(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Extract top keywords and density from page body text."""
        extra = page.get("extra_data") or {}
        body_text = extra.get("body_text", "") or ""
        word_count = page.get("word_count", 0) or 0

        if not body_text or word_count < 50:
            return {"top_keywords": [], "total_words": word_count, "keyword_density": {}}

        # Tokenize: only alphabetic words >= 3 chars
        words = re.findall(r"[a-zA-ZäöüÄÖÜß]{3,}", body_text.lower())
        filtered = [w for w in words if w not in self.STOPWORDS]

        if not filtered:
            return {"top_keywords": [], "total_words": word_count, "keyword_density": {}}

        counter = Counter(filtered)
        top10 = counter.most_common(10)
        total_filtered = len(filtered)

        keyword_density = {}
        for kw, cnt in top10:
            density = round(cnt / total_filtered * 100, 2) if total_filtered > 0 else 0
            keyword_density[kw] = density

        top_keywords = [
            {"keyword": kw, "count": cnt, "density": keyword_density.get(kw, 0)}
            for kw, cnt in top10
        ]

        return {
            "top_keywords": top_keywords,
            "total_words": word_count,
            "keyword_density": keyword_density,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _calculate_keyword_density(self, text: str, top_n: int = 5) -> List[tuple]:
        words = re.findall(r"[a-zA-Z]{3,}", text.lower())
        filtered = [w for w in words if w not in self.STOPWORDS]
        if not filtered:
            return []
        counter = Counter(filtered)
        return counter.most_common(top_n)
