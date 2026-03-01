from typing import List, Dict, Any, Optional
import re
from collections import Counter, defaultdict
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# ISO 639-1 valid language codes (subset for validation)
# ---------------------------------------------------------------------------
VALID_LANG_CODES = {
    "ab","aa","af","ak","sq","am","ar","an","hy","as","av","ae","ay","az",
    "bm","ba","eu","be","bn","bh","bi","bs","br","bg","my","ca","ch","ce",
    "ny","zh","cv","kw","co","cr","hr","cs","da","dv","nl","dz","en","eo",
    "et","ee","fo","fj","fi","fr","ff","gl","ka","de","el","gn","gu","ht",
    "ha","he","hz","hi","ho","hu","ia","id","ie","ga","ig","ik","io","is",
    "it","iu","ja","jv","kl","kn","kr","ks","kk","km","ki","rw","ky","kv",
    "kg","ko","ku","kj","la","lb","lg","li","ln","lo","lt","lu","lv","gv",
    "mk","mg","ms","ml","mt","mi","mr","mh","mn","na","nv","nd","ne","ng",
    "nb","nn","no","ii","nr","oc","oj","cu","om","or","os","pa","pi","fa",
    "pl","ps","pt","qu","rm","rn","ro","ru","sa","sc","sd","se","sm","sg",
    "sr","gd","sn","si","sk","sl","so","st","es","su","sw","ss","sv","ta",
    "te","tg","th","ti","bo","tk","tl","tn","to","tr","ts","tt","tw","ty",
    "ug","uk","ur","uz","ve","vi","vo","wa","cy","wo","fy","xh","yi","yo",
    "za","zu",
}


def _mk_issue(
    issue_type: str,
    wcag_level: str,
    wcag_version: str,
    wcag_criterion: str,
    wcag_principle: str,
    severity: str,
    title: str,
    description: str,
    affected_element: str = "",
    url: str = "",
    recommendation: str = "",
) -> Dict[str, Any]:
    """Build a standardised accessibility issue dict."""
    return {
        "type": issue_type,
        "category": "accessibility",
        "wcag_level": wcag_level,
        "wcag_version": wcag_version,
        "wcag_criterion": wcag_criterion,
        "wcag_principle": wcag_principle,
        "severity": severity,
        "title": title,
        "description": description,
        "affected_element": affected_element[:200] if affected_element else "",
        "url": url,
        "recommendation": recommendation,
        # Convenience aliases used by tasks.py / SEOIssue-compatible consumers
        "issue_type": issue_type,
    }


def _relative_luminance(r: int, g: int, b: int) -> float:
    """sRGB relative luminance per WCAG 2.x."""
    def _ch(c: int) -> float:
        v = c / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * _ch(r) + 0.7152 * _ch(g) + 0.0722 * _ch(b)


def _hex_to_rgb(hex_color: str):
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    if len(h) != 6:
        return None
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None


def calculate_contrast_ratio(color1: str, color2: str) -> Optional[float]:
    """Calculate WCAG contrast ratio between two hex colours. Returns None on parse failure."""
    rgb1 = _hex_to_rgb(color1)
    rgb2 = _hex_to_rgb(color2)
    if rgb1 is None or rgb2 is None:
        return None
    l1 = _relative_luminance(*rgb1)
    l2 = _relative_luminance(*rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# Map CSS named colors to hex (common subset)
_CSS_NAMED_COLORS = {
    "black": "#000000", "white": "#ffffff", "red": "#ff0000",
    "green": "#008000", "blue": "#0000ff", "yellow": "#ffff00",
    "orange": "#ffa500", "gray": "#808080", "grey": "#808080",
    "silver": "#c0c0c0", "navy": "#000080", "teal": "#008080",
    "purple": "#800080", "maroon": "#800000", "lime": "#00ff00",
    "aqua": "#00ffff", "fuchsia": "#ff00ff", "darkgray": "#a9a9a9",
    "darkgrey": "#a9a9a9", "lightgray": "#d3d3d3", "lightgrey": "#d3d3d3",
    "transparent": None,
}


def _css_color_to_hex(val: str) -> Optional[str]:
    """Convert CSS color value to hex string. Returns None if unparseable."""
    val = val.strip().lower()
    if val in _CSS_NAMED_COLORS:
        return _CSS_NAMED_COLORS[val]
    if val.startswith("#"):
        return val
    m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", val)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return "#{:02x}{:02x}{:02x}".format(r, g, b)
    return None


class SEOIssue:
    """Backward-compatible SEO issue object."""
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
        "a","an","the","and","or","but","in","on","at","to","for","of","with",
        "by","from","is","was","are","were","be","been","being","have","has",
        "had","do","does","did","will","would","could","should","may","might",
        "shall","can","not","this","that","these","those","it","its","as","if",
        "then","than","so","up","out","about","into","through","during","before",
        "after","above","below","between","each","more","most","other","some",
        "such","no","nor","only","same","too","very","just","also","we","you",
        "he","she","they","i","my","your","his","her","our","their","what",
        "which","who","whom","how","when","where","why","all","any","both",
        "few","own","over","under",
        "der","die","das","den","dem","des","ein","eine","einer","einem","eines",
        "und","oder","aber","nicht","mit","von","zu","bei","auf","aus","als",
        "auch","ist","sind","war","hat","haben","wird","werden","fuer","an",
        "im","sich","sie","er","es","wir","ihr","ich","du","nach","seit",
        "noch","bis","dann","wenn","dass","wie","was","kann","mehr","nur",
        "schon","alle","hier","jetzt","immer","sehr","neu","gut","ohne",
        "zwischen","unter","ueber","vor","hinter","neben","durch",
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
                    "Fix server errors immediately."))
            elif status >= 400:
                issues.append(SEOIssue(
                    "critical", "client_error",
                    "Client error: HTTP {} — page not found or inaccessible".format(status),
                    "Fix or redirect broken URLs."))
            elif status in (301, 302, 307, 308):
                redir = page.get("redirect_url", "unknown")
                issues.append(SEOIssue(
                    "warning", "redirect",
                    "Page redirects ({}) to: {}".format(status, redir),
                    "Ensure redirects point directly to the final URL."))

        if status != 200:
            return issues

        title = (page.get("title") or "").strip()
        if not title:
            issues.append(SEOIssue("critical", "missing_title",
                "Page is missing a title tag",
                "Add a unique, descriptive title tag (30-60 characters) to every page."))
        elif len(title) < self.TITLE_MIN:
            issues.append(SEOIssue("warning", "title_too_short",
                "Title too short: {} chars (min {}): '{}'".format(len(title), self.TITLE_MIN, title[:80]),
                "Expand the title to at least {} characters.".format(self.TITLE_MIN)))
        elif len(title) > self.TITLE_MAX:
            issues.append(SEOIssue("warning", "title_too_long",
                "Title too long: {} chars (max {}): '{}'..".format(len(title), self.TITLE_MAX, title[:80]),
                "Shorten the title to max {} characters.".format(self.TITLE_MAX)))

        meta = (page.get("meta_description") or "").strip()
        if not meta:
            issues.append(SEOIssue("warning", "missing_meta_description",
                "Page is missing a meta description",
                "Add a compelling meta description (70-160 characters)."))
        elif len(meta) < self.META_MIN:
            issues.append(SEOIssue("warning", "meta_description_too_short",
                "Meta description too short: {} chars (min {})".format(len(meta), self.META_MIN),
                "Expand to at least {} characters.".format(self.META_MIN)))
        elif len(meta) > self.META_MAX:
            issues.append(SEOIssue("warning", "meta_description_too_long",
                "Meta description too long: {} chars (max {})".format(len(meta), self.META_MAX),
                "Shorten to max {} characters.".format(self.META_MAX)))

        h1 = (page.get("h1") or "").strip()
        h1_count = page.get("h1_count", 0)
        if not h1:
            issues.append(SEOIssue("critical", "missing_h1", "Page is missing an H1 heading",
                "Add exactly one H1 heading."))
        elif h1_count > 1:
            issues.append(SEOIssue("warning", "multiple_h1",
                "Page has {} H1 headings (should have exactly 1)".format(h1_count),
                "Use only one H1 per page."))

        imgs_no_alt = page.get("images_without_alt", 0)
        extra = page.get("extra_data") or {}
        total_imgs = extra.get("total_images", 0) or 0
        if imgs_no_alt > 0:
            detail = " ({}/{} images)".format(imgs_no_alt, total_imgs) if total_imgs > 0 else " ({} image(s))".format(imgs_no_alt)
            issues.append(SEOIssue("warning", "images_missing_alt",
                "{} image(s) missing alt text{}".format(imgs_no_alt, detail),
                "Add descriptive alt text to all images."))

        words = page.get("word_count", 0)
        if 0 < words < 100:
            issues.append(SEOIssue("info", "low_word_count",
                "Thin content: only {} words on page".format(words),
                "Consider adding more quality content."))
        elif 100 <= words < self.THIN_CONTENT_WORDS:
            issues.append(SEOIssue("warning", "thin_content",
                "Thin content warning: only {} words (recommended: {}+)".format(words, self.THIN_CONTENT_WORDS),
                "Expand content to at least {} words.".format(self.THIN_CONTENT_WORDS)))

        rt = page.get("response_time", 0) or 0
        if rt > self.SLOW_RESPONSE_SEC:
            issues.append(SEOIssue("warning", "slow_response",
                "Slow response time: {:.2f}s (threshold: {}s)".format(rt, self.SLOW_RESPONSE_SEC),
                "Optimize server response time."))

        canonical = page.get("canonical_url")
        url = page.get("url", "")
        if canonical and canonical != url:
            issues.append(SEOIssue("info", "canonical_mismatch",
                "Canonical URL differs from page URL: {}".format(canonical),
                "Verify this canonical is intentional."))

        if url:
            parsed_url = urlparse(url)
            path = parsed_url.path
            if len(url) > self.URL_MAX_LENGTH:
                issues.append(SEOIssue("warning", "url_too_long",
                    "URL too long: {} characters (max recommended: {})".format(len(url), self.URL_MAX_LENGTH),
                    "Use shorter, descriptive URLs."))
            if re.search(r"[A-Z]", path):
                issues.append(SEOIssue("warning", "url_has_uppercase",
                    "URL path contains uppercase letters: {}".format(path[:100]),
                    "Use lowercase letters in URLs."))
            if " " in url or "%20" in url:
                issues.append(SEOIssue("warning", "url_has_spaces",
                    "URL contains spaces or encoded spaces (%20)",
                    "Replace spaces with hyphens in URL slugs."))
            depth_slashes = path.rstrip("/").count("/")
            if depth_slashes >= 5:
                issues.append(SEOIssue("info", "deep_url",
                    "URL is deeply nested ({} levels deep): {}".format(depth_slashes, path[:100]),
                    "Keep important pages within 3-4 clicks from homepage."))

        is_indexable = page.get("is_indexable", True)
        if not is_indexable:
            issues.append(SEOIssue("warning", "noindex",
                "Page has noindex directive",
                "Verify this noindex is intentional."))

        if not extra.get("og_title"):
            issues.append(SEOIssue("warning", "missing_og_title",
                "Missing Open Graph og:title tag",
                "Add og:title for better social media sharing."))
        if not extra.get("og_description"):
            issues.append(SEOIssue("warning", "missing_og_description",
                "Missing Open Graph og:description tag",
                "Add og:description to control social media appearance."))
        if not extra.get("og_image"):
            issues.append(SEOIssue("warning", "missing_og_image",
                "Missing Open Graph og:image tag",
                "Add og:image (min 1200x630px) for rich social media previews."))

        if not extra.get("twitter_card"):
            issues.append(SEOIssue("info", "missing_twitter_card",
                "Missing Twitter Card meta tag",
                "Add twitter:card meta tag."))

        if not extra.get("has_jsonld") and not extra.get("has_schema_org"):
            issues.append(SEOIssue("info", "missing_structured_data",
                "No Schema.org / JSON-LD structured data found",
                "Add structured data (JSON-LD) to enable rich results."))

        body_text = extra.get("body_text", "")
        if body_text and words >= 100:
            top_keywords = self._calculate_keyword_density(body_text, top_n=5)
            if top_keywords:
                kw_str = ", ".join("{} ({}x)".format(kw, count) for kw, count in top_keywords)
                issues.append(SEOIssue("info", "keyword_density",
                    "Top keywords: {}".format(kw_str),
                    "Ensure your target keyword appears naturally in title, H1, and body."))

        nofollow_count = extra.get("nofollow_links_count", 0)
        if nofollow_count and nofollow_count > 0:
            issues.append(SEOIssue("info", "nofollow_links",
                "Page contains {} nofollow link(s)".format(nofollow_count),
                "Review nofollow links."))

        int_links = page.get("internal_links_count", 0)
        ext_links = page.get("external_links_count", 0)
        if int_links == 0 and status == 200:
            issues.append(SEOIssue("info", "no_internal_links",
                "Page has no internal links",
                "Add internal links to improve site navigation."))
        if ext_links > 100:
            issues.append(SEOIssue("info", "many_external_links",
                "Page has {} external links — unusually high".format(ext_links),
                "Review external links."))

        issues.extend(self.analyze_images(page))
        issues.extend(self.analyze_redirects(page))
        return issues

    # ------------------------------------------------------------------
    # Image SEO Analysis
    # ------------------------------------------------------------------
    def analyze_images(self, page: Dict[str, Any]) -> List[SEOIssue]:
        issues = []
        extra = page.get("extra_data") or {}
        images = extra.get("images", [])
        if not images:
            return issues

        missing_alt_urls, empty_alt_urls, long_alt_urls, no_dims_urls, broken_urls = [], [], [], [], []

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
                issues.append(SEOIssue("warning", "image_too_large",
                    "Large image ({}KB > {}KB): {}".format(size_kb, self.IMAGE_SIZE_THRESHOLD_KB, display_src),
                    "Compress images to under {}KB.".format(self.IMAGE_SIZE_THRESHOLD_KB)))

        if missing_alt_urls:
            issues.append(SEOIssue("warning", "image_missing_alt",
                "{} image(s) missing alt attribute entirely".format(len(missing_alt_urls)),
                'Add descriptive alt text to all content images. Use alt="" only for decorative images.'))
        if empty_alt_urls:
            issues.append(SEOIssue("info", "image_empty_alt",
                "{} image(s) have empty alt attribute".format(len(empty_alt_urls)),
                "If these are content images, add descriptive alt text."))
        if long_alt_urls:
            issues.append(SEOIssue("info", "image_alt_too_long",
                "{} image(s) have alt text longer than {} characters".format(len(long_alt_urls), self.IMAGE_ALT_MAX_LENGTH),
                "Keep alt text concise (under {} chars).".format(self.IMAGE_ALT_MAX_LENGTH)))
        if no_dims_urls:
            issues.append(SEOIssue("info", "image_no_dimensions",
                "{} image(s) missing width/height attributes".format(len(no_dims_urls)),
                "Add explicit width and height to all img tags."))
        for src, st in broken_urls:
            issues.append(SEOIssue("critical", "image_broken",
                "Broken image (HTTP {}): {}".format(st, src),
                "Fix or remove broken image references."))
        return issues

    # ------------------------------------------------------------------
    # Redirect Chain Analysis
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
            issues.append(SEOIssue("critical", "redirect_loop",
                "Redirect loop detected",
                "Fix the redirect configuration to eliminate circular redirects."))
        elif hops > self.REDIRECT_CHAIN_MAX_HOPS:
            issues.append(SEOIssue("warning", "redirect_chain_too_long",
                "Redirect chain too long: {} hops (max recommended: {})".format(hops, self.REDIRECT_CHAIN_MAX_HOPS),
                "Shorten redirect chains to a single redirect."))
        return issues

    # ------------------------------------------------------------------
    # Duplicate Content Detection
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
    # Feature 4: Accessibility Analysis — WCAG 2.1 + 2.2 (A / AA / AAA)
    # ------------------------------------------------------------------
    def analyze_accessibility(self, page: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Full WCAG 2.1 + 2.2 Level A / AA / AAA accessibility analysis.
        Reads pre-extracted a11y data from spider extra_data['a11y'].
        Returns a list of issue dicts with complete WCAG metadata."""
        issues: List[Dict[str, Any]] = []
        extra = page.get("extra_data") or {}
        a11y = extra.get("a11y") or {}
        url = page.get("url", "")

        if not a11y:
            return issues

        def add(issue_type, lvl, ver, criterion, principle, sev, title, desc,
                elem="", rec=""):
            issues.append(_mk_issue(
                issue_type=issue_type, wcag_level=lvl, wcag_version=ver,
                wcag_criterion=criterion, wcag_principle=principle,
                severity=sev, title=title, description=desc,
                affected_element=elem, url=url, recommendation=rec,
            ))

        # ================================================================
        # PERCEIVABLE
        # ================================================================

        # --- 1.1.1 Non-text Content (A) ---
        missing_alt = a11y.get("images_missing_alt", [])
        for src in missing_alt:
            add("wcag_A_21_111_img_missing_alt", "A", "2.1", "1.1.1", "perceivable",
                "critical", "Bild ohne Alt-Text",
                "Das Bild '{}' hat kein alt-Attribut und verstößt gegen WCAG 1.1.1.".format(src[:80]),
                "<img src=\"{}\">".format(src[:100]),
                "Füge alt=\"Beschreibung\" zu allen nicht-dekorativen Bildern hinzu.")

        img_input_no_alt = a11y.get("img_input_missing_alt", [])
        for elem in img_input_no_alt:
            add("wcag_A_21_111_input_image_missing_alt", "A", "2.1", "1.1.1", "perceivable",
                "critical", "input[type=image] ohne Alt-Text",
                "Ein Bild-Eingabefeld hat kein alt-Attribut (WCAG 1.1.1).",
                elem[:200],
                "Füge ein aussagekräftiges alt-Attribut zum Bild-Button hinzu.")

        area_no_alt = a11y.get("area_missing_alt", [])
        for elem in area_no_alt:
            add("wcag_A_21_111_area_missing_alt", "A", "2.1", "1.1.1", "perceivable",
                "critical", "<area> ohne Alt-Text",
                "Ein <area>-Element in einer Image-Map hat kein alt-Attribut (WCAG 1.1.1).",
                elem[:200],
                "Füge ein alt-Attribut zu allen <area>-Elementen hinzu.")

        empty_alt_non_deco = a11y.get("images_empty_alt_non_decorative", [])
        for src in empty_alt_non_deco:
            add("wcag_A_21_111_img_empty_alt_nondeco", "A", "2.1", "1.1.1", "perceivable",
                "warning", "Nicht-dekoratives Bild mit leerem Alt-Text",
                "Bild '{}' hat alt=\"\" ist aber kein dekoratives Element (WCAG 1.1.1).".format(src[:80]),
                "<img src=\"{}\" alt=\"\">".format(src[:100]),
                "Füge einen beschreibenden Alt-Text hinzu oder markiere das Bild als dekorativ mit role='presentation'.")

        svg_no_title = a11y.get("svg_missing_accessible_name", [])
        for elem in svg_no_title:
            add("wcag_A_21_111_svg_missing_name", "A", "2.1", "1.1.1", "perceivable",
                "warning", "SVG ohne barrierefreien Namen",
                "Ein <svg>-Element hat weder <title> noch aria-label (WCAG 1.1.1).",
                elem[:200],
                "Füge <title> oder aria-label zu informativen SVGs hinzu.")

        obj_no_text = a11y.get("object_embed_no_text", [])
        for elem in obj_no_text:
            add("wcag_A_21_111_object_no_text_alt", "A", "2.1", "1.1.1", "perceivable",
                "warning", "<object>/<embed> ohne Textalternative",
                "Ein <object>- oder <embed>-Element enthält keine Textalternative (WCAG 1.1.1).",
                elem[:200],
                "Füge einen beschreibenden Textinhalt oder aria-label hinzu.")

        # --- 1.2.1 Audio-only / Video-only (A) ---
        audio_no_transcript = a11y.get("audio_missing_transcript_hint", [])
        for elem in audio_no_transcript:
            add("wcag_A_21_121_audio_no_transcript", "A", "2.1", "1.2.1", "perceivable",
                "warning", "Audio ohne Transkript-Hinweis",
                "Ein <audio>-Element hat keinen Track, kein aria-describedby und keinen sichtbaren Transkript-Link (WCAG 1.2.1).",
                elem[:200],
                "Verlinke ein vollständiges Transkript oder füge <track kind='descriptions'> hinzu.")

        video_no_controls = a11y.get("video_missing_controls", [])
        for elem in video_no_controls:
            add("wcag_A_21_121_video_no_controls", "A", "2.1", "1.2.1", "perceivable",
                "info", "Video ohne controls-Attribut",
                "Ein <video>-Element hat kein controls-Attribut (WCAG 1.2.1).",
                elem[:200],
                "Füge das controls-Attribut hinzu, damit Nutzer das Video steuern können.")

        # --- 1.2.2 Captions (A) ---
        video_no_captions = a11y.get("video_missing_captions", [])
        for elem in video_no_captions:
            add("wcag_A_21_122_video_no_captions", "A", "2.1", "1.2.2", "perceivable",
                "critical", "Video ohne Untertitel-Track",
                "Ein <video>-Element hat keinen <track kind='captions'>-Track (WCAG 1.2.2).",
                elem[:200],
                "Füge <track kind='captions' src='...' srclang='de'> zum Video hinzu.")

        # --- 1.2.3 Audio Description (A) ---
        video_no_desc_a = a11y.get("video_missing_audio_description", [])
        for elem in video_no_desc_a:
            add("wcag_A_21_123_video_no_audio_desc", "A", "2.1", "1.2.3", "perceivable",
                "info", "Video ohne Audiobeschreibungs-Track",
                "Ein <video>-Element hat keinen <track kind='descriptions'>-Track (WCAG 1.2.3).",
                elem[:200],
                "Füge <track kind='descriptions'> als Audiobeschreibung hinzu.")

        # --- 1.2.5 Audio Description AA ---
        for elem in video_no_desc_a:
            add("wcag_AA_21_125_video_no_audio_desc", "AA", "2.1", "1.2.5", "perceivable",
                "warning", "Video ohne Audiobeschreibung (AA)",
                "WCAG 1.2.5 (AA) erfordert eine Audiobeschreibung für alle voraufgezeichneten Videos.",
                elem[:200],
                "Erstelle eine vollständige Audiobeschreibungsspur für das Video.")

        # --- 1.3.1 Info and Relationships (A) ---
        inputs_no_label = a11y.get("inputs_missing_label", [])
        for inp in inputs_no_label:
            inp_type = inp.get("type", "text") if isinstance(inp, dict) else "input"
            inp_name = inp.get("name", "") if isinstance(inp, dict) else ""
            elem_str = "<input type='{}' name='{}'>".format(inp_type, inp_name)
            add("wcag_A_21_131_input_missing_label", "A", "2.1", "1.3.1", "perceivable",
                "critical", "Formulareingabe ohne Label",
                "Ein Eingabefeld (type={}) hat kein zugeordnetes Label (WCAG 1.3.1).".format(inp_type),
                elem_str,
                "Füge <label for='id'> oder aria-label zu jedem Eingabefeld hinzu.")

        tables_no_th = a11y.get("tables_missing_th", [])
        for elem in tables_no_th:
            add("wcag_A_21_131_table_no_th", "A", "2.1", "1.3.1", "perceivable",
                "warning", "Datentabelle ohne Tabellenheader",
                "Eine Datentabelle enthält keine <th>-Elemente (WCAG 1.3.1).",
                elem[:200],
                "Füge <th scope='col'> oder <th scope='row'> für alle Spalten-/Zeilenüberschriften hinzu.")

        tables_no_caption = a11y.get("tables_missing_caption", [])
        for elem in tables_no_caption:
            add("wcag_A_21_131_table_no_caption", "A", "2.1", "1.3.1", "perceivable",
                "info", "Tabelle ohne Beschriftung",
                "Eine Tabelle hat weder <caption> noch aria-label (WCAG 1.3.1).",
                elem[:200],
                "Füge <caption> oder aria-label zur Tabelle hinzu.")

        th_no_scope = a11y.get("th_missing_scope", [])
        for elem in th_no_scope:
            add("wcag_A_21_131_th_no_scope", "A", "2.1", "1.3.1", "perceivable",
                "warning", "<th> ohne scope-Attribut in komplexer Tabelle",
                "Ein <th>-Element in einer komplexen Tabelle hat kein scope-Attribut (WCAG 1.3.1).",
                elem[:200],
                "Füge scope='col', scope='row', scope='colgroup' oder scope='rowgroup' hinzu.")

        selects_no_label = a11y.get("select_missing_label", [])
        for s in selects_no_label:
            name = s if isinstance(s, str) else str(s)
            add("wcag_A_21_131_select_missing_label", "A", "2.1", "1.3.1", "perceivable",
                "warning", "<select> ohne Label",
                "Ein <select>-Element (name='{}') hat kein zugeordnetes Label (WCAG 1.3.1).".format(name[:40]),
                "<select name='{}'>".format(name[:40]),
                "Füge <label for='id'> oder aria-label zum Select-Element hinzu.")

        textarea_no_label = a11y.get("textarea_missing_label", [])
        for elem in textarea_no_label:
            add("wcag_A_21_131_textarea_missing_label", "A", "2.1", "1.3.1", "perceivable",
                "critical", "<textarea> ohne Label",
                "Ein <textarea>-Element hat kein zugeordnetes Label (WCAG 1.3.1).",
                elem[:200],
                "Füge <label for='id'> oder aria-label zur Textarea hinzu.")

        fieldset_no_legend = a11y.get("fieldset_missing_legend", [])
        for elem in fieldset_no_legend:
            add("wcag_A_21_131_fieldset_no_legend", "A", "2.1", "1.3.1", "perceivable",
                "warning", "<fieldset> ohne <legend>",
                "Ein <fieldset>-Element hat keine <legend>-Überschrift (WCAG 1.3.1).",
                elem[:200],
                "Füge <legend> als erstes Kind des <fieldset> hinzu.")

        # --- 1.3.2 Meaningful Sequence (A) ---
        layout_tables = a11y.get("layout_tables", [])
        if layout_tables:
            add("wcag_A_21_132_layout_table", "A", "2.1", "1.3.2", "perceivable",
                "info", "Tabellen für Layout verwendet",
                "{} Tabelle(n) werden wahrscheinlich für das Seitenlayout verwendet, nicht für Daten (WCAG 1.3.2).".format(len(layout_tables)),
                "",
                "Verwende CSS für das Layout statt Tabellen.")

        # --- 1.3.3 Sensory Characteristics (A) ---
        sensory_refs = a11y.get("sensory_characteristics_text", [])
        for ref in sensory_refs:
            add("wcag_A_21_133_sensory_ref", "A", "2.1", "1.3.3", "perceivable",
                "info", "Hinweis auf sensorische Eigenschaften",
                "Text enthält einen rein positions- oder farbbasierten Verweis: '{}' (WCAG 1.3.3).".format(ref[:80]),
                ref[:200],
                "Ergänze den Hinweis durch nicht-sensorische Informationen (z.B. Label, Form, Funktion).")

        # --- 1.3.4 Orientation (AA, WCAG 2.1) ---
        if a11y.get("orientation_locked"):
            add("wcag_AA_21_134_orientation_locked", "AA", "2.1", "1.3.4", "perceivable",
                "warning", "Orientierung gesperrt",
                "Die Seite sperrt die Anzeigeorientierung auf Hoch- oder Querformat (WCAG 1.3.4).",
                "",
                "Entferne CSS- oder JS-basierte Orientierungssperren.")

        # --- 1.3.5 Identify Input Purpose (AA, WCAG 2.1) ---
        inputs_no_autocomplete = a11y.get("inputs_missing_autocomplete", [])
        for inp in inputs_no_autocomplete:
            inp_type = inp.get("type", "") if isinstance(inp, dict) else str(inp)
            inp_name = inp.get("name", "") if isinstance(inp, dict) else ""
            add("wcag_AA_21_135_input_no_autocomplete", "AA", "2.1", "1.3.5", "perceivable",
                "warning", "Eingabefeld ohne autocomplete-Attribut",
                "Eingabefeld type='{}' name='{}' fehlt das autocomplete-Attribut (WCAG 1.3.5).".format(inp_type, inp_name[:40]),
                "<input type='{}' name='{}'>".format(inp_type, inp_name[:40]),
                "Füge autocomplete='email', 'tel', 'name' etc. zum Eingabefeld hinzu.")

        # --- 1.4.1 Use of Color (A) ---
        links_no_underline = a11y.get("links_no_underline_no_aria", [])
        if links_no_underline:
            add("wcag_A_21_141_link_no_underline", "A", "2.1", "1.4.1", "perceivable",
                "warning", "Links ohne Unterstreichung",
                "{} Link(s) sind nicht unterstrichen und ohne ARIA-Rolle – Farbe ist der einzige Unterschied (WCAG 1.4.1).".format(len(links_no_underline)),
                "",
                "Unterstreiche Links oder füge eine andere nicht-farbbasierte visuelle Unterscheidung hinzu.")

        # --- 1.4.2 Audio Control (A) ---
        audio_autoplay = a11y.get("audio_autoplay", [])
        for elem in audio_autoplay:
            add("wcag_A_21_142_audio_autoplay", "A", "2.1", "1.4.2", "perceivable",
                "critical", "Audio startet automatisch",
                "Ein <audio>-Element startet automatisch ohne Nutzerinteraktion (WCAG 1.4.2).",
                elem[:200],
                "Entferne das autoplay-Attribut oder biete eine klare Stopp-Funktion an.")

        video_autoplay = a11y.get("video_autoplay", [])
        for elem in video_autoplay:
            add("wcag_A_21_142_video_autoplay", "A", "2.1", "1.4.2", "perceivable",
                "warning", "Video startet automatisch",
                "Ein <video>-Element startet automatisch (WCAG 1.4.2).",
                elem[:200],
                "Entferne autoplay oder füge muted+autoplay nur für dekorative Videos hinzu.")

        # --- 1.4.3 Contrast (AA) – inline styles only ---
        contrast_issues = a11y.get("contrast_issues", [])
        for ci in contrast_issues:
            ratio = ci.get("ratio", 0)
            add("wcag_AA_21_143_contrast_insufficient", "AA", "2.1", "1.4.3", "perceivable",
                "warning", "Unzureichender Farbkontrast (Inline-Style)",
                "Kontrastverhältnis {:.2f}:1 unterschreitet den WCAG-Mindestwert (WCAG 1.4.3). Element: {}".format(
                    ratio, ci.get("element", "")[:80]),
                ci.get("element", "")[:200],
                "Erhöhe den Kontrast auf mindestens 4.5:1 für Normaltext oder 3:1 für großen Text.")

        # --- 1.4.4 Resize Text (AA) ---
        if a11y.get("viewport_no_scale"):
            add("wcag_AA_21_144_viewport_no_scale", "AA", "2.1", "1.4.4", "perceivable",
                "critical", "Viewport sperrt Zoom (user-scalable=no)",
                "Der viewport-Meta-Tag enthält user-scalable=no und verhindert Zoom für Sehbehinderte (WCAG 1.4.4).",
                "<meta name='viewport' content='user-scalable=no'>",
                "Entferne user-scalable=no aus dem viewport-Meta-Tag.")

        max_scale = a11y.get("viewport_max_scale")
        if max_scale is not None and max_scale < 2.0:
            add("wcag_AA_21_144_viewport_max_scale", "AA", "2.1", "1.4.4", "perceivable",
                "warning", "Viewport maximum-scale zu niedrig",
                "viewport maximum-scale={} erlaubt zu wenig Zoom (mind. 2.0 empfohlen, WCAG 1.4.4).".format(max_scale),
                "<meta name='viewport' content='maximum-scale={}'>".format(max_scale),
                "Setze maximum-scale auf mindestens 2.0 oder entferne die Einschränkung.")

        px_font_count = a11y.get("inline_px_font_count", 0)
        if px_font_count > 0:
            add("wcag_AA_21_144_px_font_sizes", "AA", "2.1", "1.4.4", "perceivable",
                "info", "Schriftgrößen in px statt em/rem",
                "{} Inline-Style(s) verwenden Schriftgrößen in px, die sich beim Zoom-Text schlechter skalieren (WCAG 1.4.4).".format(px_font_count),
                "",
                "Verwende relative Einheiten (em, rem) für Schriftgrößen.")

        # --- 1.4.6 Enhanced Contrast (AAA) ---
        contrast_aaa_issues = a11y.get("contrast_aaa_issues", [])
        for ci in contrast_aaa_issues:
            ratio = ci.get("ratio", 0)
            add("wcag_AAA_21_146_contrast_enhanced", "AAA", "2.1", "1.4.6", "perceivable",
                "info", "Kontrast unter AAA-Schwellenwert (7:1)",
                "Kontrastverhältnis {:.2f}:1 liegt unter dem AAA-Wert von 7:1 (WCAG 1.4.6).".format(ratio),
                ci.get("element", "")[:200],
                "Erhöhe den Kontrast auf mindestens 7:1 für AAA-Konformität.")

        # --- 1.4.8 Visual Presentation (AAA) ---
        justified_text = a11y.get("justified_text_count", 0)
        if justified_text > 0:
            add("wcag_AAA_21_148_justified_text", "AAA", "2.1", "1.4.8", "perceivable",
                "info", "Blocksatz-Text",
                "{} Element(e) verwenden text-align:justify, was das Lesen erschwert (WCAG 1.4.8).".format(justified_text),
                "",
                "Vermeide Blocksatz für Textabsätze.")

        # --- 1.4.10 Reflow (AA, WCAG 2.1) ---
        reflow_issues = a11y.get("reflow_fixed_width", [])
        for elem in reflow_issues:
            add("wcag_AA_21_1410_reflow_fixed_width", "AA", "2.1", "1.4.10", "perceivable",
                "warning", "Erzwungenes horizontales Scrollen",
                "Inline-Style setzt eine feste Breite, die horizontales Scrollen erzwingt (WCAG 1.4.10).",
                elem[:200],
                "Verwende responsive Einheiten (%, vw, max-width) statt fixer Pixelbreiten.")

        # --- 1.4.12 Text Spacing (AA, WCAG 2.1) ---
        text_spacing_important = a11y.get("text_spacing_important", [])
        for elem in text_spacing_important:
            add("wcag_AA_21_1412_text_spacing_important", "AA", "2.1", "1.4.12", "perceivable",
                "warning", "!important bei Text-Abstand-Eigenschaften",
                "!important auf line-height/letter-spacing verhindert benutzerangepasste Textabstände (WCAG 1.4.12).",
                elem[:200],
                "Entferne !important von Text-Abstand-Eigenschaften.")

        # --- 1.4.13 Content on Hover or Focus (AA, WCAG 2.1) ---
        title_as_tooltip = a11y.get("title_as_primary_info", [])
        for elem in title_as_tooltip:
            add("wcag_AA_21_1413_title_as_primary", "AA", "2.1", "1.4.13", "perceivable",
                "info", "title-Attribut als primäre Informationsquelle",
                "Das title-Attribut wird als primäre Information verwendet – es ist per Tastatur nicht zugänglich (WCAG 1.4.13).",
                elem[:200],
                "Verwende sichtbaren Text oder ARIA statt title für wichtige Informationen.")

        # ================================================================
        # OPERABLE
        # ================================================================

        # --- 2.1.1 Keyboard (A) ---
        onclick_nonfocusable = a11y.get("onclick_nonfocusable", [])
        for elem in onclick_nonfocusable:
            add("wcag_A_21_211_onclick_nonfocusable", "A", "2.1", "2.1.1", "operable",
                "warning", "onclick auf nicht fokussierbarem Element",
                "Ein onclick-Handler auf einem nicht fokussierbaren Element ohne tabindex/role macht die Funktion per Tastatur nicht erreichbar (WCAG 2.1.1).",
                elem[:200],
                "Verwende <button> oder füge tabindex='0' und role='button' hinzu.")

        mouseover_no_focus = a11y.get("onmouseover_no_onfocus", [])
        for elem in mouseover_no_focus:
            add("wcag_A_21_211_mouseover_no_focus", "A", "2.1", "2.1.1", "operable",
                "warning", "onmouseover ohne onfocus-Entsprechung",
                "Ein onmouseover-Handler hat kein onfocus-Gegenstück (WCAG 2.1.1).",
                elem[:200],
                "Füge einen entsprechenden onfocus-Handler hinzu.")

        ondblclick_elems = a11y.get("ondblclick_elements", [])
        if ondblclick_elems:
            add("wcag_A_21_211_ondblclick", "A", "2.1", "2.1.1", "operable",
                "info", "Doppelklick-Ereignis",
                "{} Element(e) verwenden ondblclick, was per Tastatur nicht reproduzierbar ist (WCAG 2.1.1).".format(len(ondblclick_elems)),
                "",
                "Biete eine Tastaturalternative für alle Doppelklick-Aktionen an.")

        # --- 2.1.3 Keyboard No Exception (AAA) ---
        draggable_no_kb = a11y.get("draggable_no_keyboard", [])
        for elem in draggable_no_kb:
            add("wcag_AAA_21_213_drag_no_keyboard", "AAA", "2.1", "2.1.3", "operable",
                "warning", "Drag-and-Drop ohne Tastaturalternative",
                "Ein draggable-Element hat keinen Tastatur-Handler (WCAG 2.1.3).",
                elem[:200],
                "Implementiere eine Tastaturalternative für alle Drag-and-Drop-Aktionen.")

        # --- 2.2.1 Timing Adjustable (A) ---
        meta_refresh = a11y.get("meta_refresh", [])
        for elem in meta_refresh:
            add("wcag_A_21_221_meta_refresh", "A", "2.1", "2.2.1", "operable",
                "critical", "Automatischer Meta-Refresh",
                "Ein <meta http-equiv='refresh'> leitet die Seite automatisch weiter (WCAG 2.2.1).",
                elem[:200],
                "Entferne Meta-Refresh. Nutze serverseitige Weiterleitungen oder gib dem Nutzer die Kontrolle.")

        # --- 2.2.2 Pause, Stop, Hide (A) ---
        marquee_blink = a11y.get("marquee_blink", [])
        for elem in marquee_blink:
            add("wcag_A_21_222_marquee_blink", "A", "2.1", "2.2.2", "operable",
                "critical", "Veraltetes bewegtes Element",
                "<marquee> oder <blink> erzeugen automatisch bewegte Inhalte ohne Stopp-Möglichkeit (WCAG 2.2.2).",
                elem[:200],
                "Entferne <marquee> und <blink>. Verwende CSS-Animationen mit prefers-reduced-motion.")

        # --- 2.2.4 Interruptions (AAA) ---
        auto_refresh_no_control = a11y.get("auto_refresh_no_control", [])
        for elem in auto_refresh_no_control:
            add("wcag_AAA_21_224_auto_refresh", "AAA", "2.1", "2.2.4", "operable",
                "warning", "Automatische Aktualisierung ohne Benutzersteuerung",
                "Die Seite aktualisiert sich automatisch ohne Möglichkeit für den Nutzer, dies zu steuern (WCAG 2.2.4).",
                elem[:200],
                "Biete eine Möglichkeit, automatische Aktualisierungen zu deaktivieren oder zu verschieben.")

        # --- 2.4.1 Bypass Blocks (A) ---
        if not a11y.get("skip_nav_found"):
            add("wcag_A_21_241_no_skip_link", "A", "2.1", "2.4.1", "operable",
                "warning", "Kein Skip-Navigation-Link",
                "Die Seite hat keinen 'Zum Hauptinhalt springen'-Link vor der Navigation (WCAG 2.4.1).",
                "",
                "Füge einen Skip-Link als erstes fokussierbares Element der Seite ein.")

        landmark_missing = a11y.get("landmark_regions_missing", [])
        for lm in landmark_missing:
            add("wcag_A_21_241_missing_landmark", "A", "2.1", "2.4.1", "operable",
                "warning", "Fehlende Landmark-Region: {}".format(lm),
                "Die semantische Region <{}> fehlt auf der Seite (WCAG 2.4.1).".format(lm),
                "",
                "Füge <{}> oder role='{}' als Landmark-Region hinzu.".format(lm, lm))

        # --- 2.4.2 Page Titled (A) ---
        title = (page.get("title") or "").strip()
        if not title:
            add("wcag_A_21_242_missing_title", "A", "2.1", "2.4.2", "operable",
                "critical", "Seitentitel fehlt",
                "Die Seite hat keinen <title>-Tag (WCAG 2.4.2).",
                "<title></title>",
                "Füge einen beschreibenden <title> zu jeder HTML-Seite hinzu.")
        elif title.lower() in ("untitled", "untitled document", "neue seite", "new page", ""):
            add("wcag_A_21_242_placeholder_title", "A", "2.1", "2.4.2", "operable",
                "warning", "Seitentitel ist ein Platzhalter",
                "Der Seitentitel lautet '{}' und ist kein beschreibender Titel (WCAG 2.4.2).".format(title),
                "<title>{}</title>".format(title),
                "Ersetze den Platzhalter-Titel durch einen eindeutigen, beschreibenden Titel.")

        # --- 2.4.3 Focus Order (A) ---
        pos_tabindex = a11y.get("positive_tabindex", [])
        for item in pos_tabindex:
            tag = item.get("tag", "element") if isinstance(item, dict) else "element"
            val = item.get("tabindex", "") if isinstance(item, dict) else str(item)
            add("wcag_A_21_243_positive_tabindex", "A", "2.1", "2.4.3", "operable",
                "warning", "Positiver tabindex-Wert",
                "<{}> hat tabindex={} und stört die natürliche Tab-Reihenfolge (WCAG 2.4.3).".format(tag, val),
                "<{} tabindex='{}'>".format(tag, val),
                "Entferne positive tabindex-Werte. Verwende nur tabindex='0' oder '-1'.")

        # --- 2.4.4 Link Purpose (A) ---
        vague_links = a11y.get("vague_links", [])
        for lnk in vague_links:
            txt = lnk.get("text", "") if isinstance(lnk, dict) else str(lnk)
            href = lnk.get("href", "") if isinstance(lnk, dict) else ""
            add("wcag_A_21_244_vague_link_text", "A", "2.1", "2.4.4", "operable",
                "warning", "Vager Linktext",
                "Link-Text '{}' ist zu vage und beschreibt das Ziel nicht ausreichend (WCAG 2.4.4).".format(txt),
                "<a href='{}'>{}</a>".format(href[:80], txt),
                "Verwende beschreibenden Linktext der das Ziel erklärt.")

        empty_links = a11y.get("empty_links", [])
        for href in empty_links:
            add("wcag_A_21_244_empty_link", "A", "2.1", "2.4.4", "operable",
                "critical", "Leerer Link ohne Text oder aria-label",
                "Ein Link hat weder sichtbaren Text noch aria-label (WCAG 2.4.4).",
                "<a href='{}'></a>".format(href[:80] if isinstance(href, str) else ""),
                "Füge beschreibenden Text oder aria-label zu allen Links hinzu.")

        icon_links = a11y.get("icon_links_no_aria", [])
        for href in icon_links:
            add("wcag_A_21_244_icon_link_no_aria", "A", "2.1", "2.4.4", "operable",
                "warning", "Icon-Link ohne aria-label",
                "Ein Icon-Only-Link hat kein aria-label (WCAG 2.4.4).",
                "<a href='{}'><i class='icon...'></i></a>".format(href[:80] if isinstance(href, str) else ""),
                "Füge aria-label='Linkbeschreibung' zum Icon-Link hinzu.")

        # --- 2.4.5 Multiple Ways (AA) ---
        if not a11y.get("has_search") and not a11y.get("has_sitemap_link") and not a11y.get("has_breadcrumb"):
            add("wcag_AA_21_245_no_multiple_ways", "AA", "2.1", "2.4.5", "operable",
                "info", "Kein alternativer Navigationsweg",
                "Die Seite bietet keine Suche, Sitemap oder Breadcrumb-Navigation (WCAG 2.4.5).",
                "",
                "Biete mindestens zwei Wege zur Navigation an: Suche, Sitemap oder Breadcrumb.")

        # --- 2.4.6 Headings and Labels (AA) ---
        empty_headings = a11y.get("empty_headings", [])
        for elem in empty_headings:
            add("wcag_AA_21_246_empty_heading", "AA", "2.1", "2.4.6", "operable",
                "critical", "Leere Überschrift",
                "Eine Überschrift (h1–h6) ist leer oder enthält nur Whitespace (WCAG 2.4.6).",
                elem[:200],
                "Füge beschreibenden Text zur Überschrift hinzu oder entferne das leere Tag.")

        heading_skip = a11y.get("heading_hierarchy_skip", [])
        for skip in heading_skip:
            add("wcag_AA_21_246_heading_skip", "AA", "2.1", "2.4.6", "operable",
                "warning", "Übersprungene Überschriftenebene",
                "Die Überschriftenhierarchie springt von {} auf {} ohne Zwischenebene (WCAG 2.4.6).".format(
                    skip.get("from", "?"), skip.get("to", "?")) if isinstance(skip, dict) else str(skip),
                "",
                "Verwende Überschriften in aufsteigender Reihenfolge (h1 → h2 → h3 ...).")

        # --- 2.4.7 Focus Visible (AA) ---
        outline_none = a11y.get("outline_none_no_alternative", [])
        for elem in outline_none:
            add("wcag_AA_21_247_outline_none", "AA", "2.1", "2.4.7", "operable",
                "warning", "outline:none ohne :focus-visible-Alternative",
                "Ein Inline-Style setzt outline:none und entfernt den sichtbaren Fokus-Indikator (WCAG 2.4.7).",
                elem[:200],
                "Entferne outline:none oder definiere :focus-visible mit einem sichtbaren Fokus-Indikator.")

        # --- 2.4.8 Location (AAA) ---
        if not a11y.get("has_breadcrumb"):
            add("wcag_AAA_21_248_no_breadcrumb", "AAA", "2.1", "2.4.8", "operable",
                "info", "Keine Breadcrumb-Navigation",
                "Die Seite zeigt keine Breadcrumb-Navigation zur Standortanzeige (WCAG 2.4.8).",
                "",
                "Füge eine Breadcrumb-Navigation zur Orientierung hinzu.")

        # --- 2.4.9 Link Purpose Link Only (AAA) ---
        for lnk in vague_links:
            txt = lnk.get("text", "") if isinstance(lnk, dict) else str(lnk)
            add("wcag_AAA_21_249_link_purpose_only", "AAA", "2.1", "2.4.9", "operable",
                "info", "Linktext nicht selbsterklärend (AAA)",
                "Link-Text '{}' ist auch ohne Kontext nicht eindeutig (WCAG 2.4.9).".format(txt),
                "",
                "Wähle Linktexte, die das Ziel auch ohne umliegenden Kontext verständlich machen.")

        # --- 2.4.10 Section Headings (AAA) ---
        sections_no_heading = a11y.get("sections_without_headings", 0)
        if sections_no_heading > 0:
            add("wcag_AAA_21_2410_section_no_heading", "AAA", "2.1", "2.4.10", "operable",
                "info", "Inhaltsbereich ohne Überschrift",
                "{} Inhaltsbereich(e) ohne Überschrift gefunden (WCAG 2.4.10).".format(sections_no_heading),
                "",
                "Füge jeder inhaltlichen Sektion eine Überschrift (h2–h6) hinzu.")

        # --- 2.4.11 Focus Not Obscured (AA, WCAG 2.2) ---
        sticky_no_scroll_padding = a11y.get("sticky_header_no_scroll_padding")
        if sticky_no_scroll_padding:
            add("wcag_AA_22_2411_focus_obscured", "AA", "2.2", "2.4.11", "operable",
                "info", "Fokus durch sticky Header verdeckt",
                "Die Seite hat einen sticky Header ohne entsprechendes scroll-padding (WCAG 2.4.11).",
                "",
                "Setze scroll-padding-top entsprechend der Header-Höhe.")

        # --- 2.5.3 Label in Name (A/AA, WCAG 2.1) ---
        label_mismatch = a11y.get("label_in_name_mismatch", [])
        for item in label_mismatch:
            visible = item.get("visible", "") if isinstance(item, dict) else ""
            aria = item.get("aria", "") if isinstance(item, dict) else ""
            add("wcag_A_21_253_label_name_mismatch", "A", "2.1", "2.5.3", "operable",
                "warning", "Label in Name – Sichtbarer Text stimmt nicht mit aria-label überein",
                "Sichtbarer Text '{}' stimmt nicht mit aria-label '{}' überein (WCAG 2.5.3).".format(visible[:40], aria[:40]),
                "",
                "Stelle sicher, dass aria-label den sichtbaren Text enthält.")

        # ================================================================
        # UNDERSTANDABLE
        # ================================================================

        # --- 3.1.1 Language of Page (A) ---
        html_lang = a11y.get("html_lang", "")
        if a11y.get("html_lang_missing"):
            add("wcag_A_21_311_missing_lang", "A", "2.1", "3.1.1", "understandable",
                "critical", "<html> ohne lang-Attribut",
                "Das <html>-Element hat kein lang-Attribut (WCAG 3.1.1).",
                "<html>",
                "Füge lang='de' (oder den entsprechenden Sprachcode) zum <html>-Tag hinzu.")
        elif a11y.get("html_lang_invalid"):
            add("wcag_A_21_311_invalid_lang", "A", "2.1", "3.1.1", "understandable",
                "warning", "Ungültiger Sprachcode im lang-Attribut",
                "Das lang-Attribut '{}' ist kein gültiger ISO 639-1 Sprachcode (WCAG 3.1.1).".format(html_lang),
                "<html lang='{}'>".format(html_lang),
                "Verwende einen gültigen BCP 47-Sprachcode (z.B. 'de', 'en', 'de-DE').")

        # --- 3.2.1 On Focus (A) ---
        onfocus_nav = a11y.get("onfocus_navigation", [])
        for elem in onfocus_nav:
            add("wcag_A_21_321_onfocus_navigation", "A", "2.1", "3.2.1", "understandable",
                "warning", "Kontextwechsel bei Fokus",
                "Ein onfocus-Handler löst Navigation oder Formular-Submit aus (WCAG 3.2.1).",
                elem[:200],
                "Entferne automatische Navigation im onfocus-Handler.")

        # --- 3.2.2 On Input (A) ---
        onchange_nav = a11y.get("onchange_navigation", [])
        for elem in onchange_nav:
            add("wcag_A_21_322_onchange_navigation", "A", "2.1", "3.2.2", "understandable",
                "warning", "Kontextwechsel bei Eingabe",
                "Ein onchange-Handler auf einem <select> löst eine Seitennavigation aus (WCAG 3.2.2).",
                elem[:200],
                "Füge einen Submit-Button hinzu statt automatischer Navigation bei Auswahl.")

        # --- 3.2.5 Change on Request (AAA) ---
        blank_links = a11y.get("links_target_blank_no_warning", [])
        for elem in blank_links:
            add("wcag_AAA_21_325_target_blank", "AAA", "2.1", "3.2.5", "understandable",
                "info", "Link öffnet neues Fenster ohne Warnung",
                "Ein Link mit target='_blank' warnt den Nutzer nicht über das neue Fenster (WCAG 3.2.5).",
                elem[:200],
                "Weise Nutzer darauf hin, dass der Link in einem neuen Tab/Fenster öffnet.")

        # --- 3.2.6 Consistent Help (AA, WCAG 2.2) ---
        if not a11y.get("has_contact_link") and not a11y.get("has_help_link"):
            add("wcag_AA_22_326_no_consistent_help", "AA", "2.2", "3.2.6", "understandable",
                "info", "Keine konsistente Hilfe verfügbar",
                "Die Seite bietet keinen Kontakt- oder Hilfe-Link (WCAG 3.2.6).",
                "",
                "Füge konsistente Hilfe (Kontakt, Telefon, Chat) zu allen Seiten hinzu.")

        # --- 3.3.1 Error Identification (A) ---
        required_no_error = a11y.get("required_inputs_no_error_pattern", [])
        if required_no_error:
            add("wcag_A_21_331_required_no_error", "A", "2.1", "3.3.1", "understandable",
                "info", "Pflichtfeld ohne Fehlerbeschreibungs-Muster",
                "{} Pflichtfeld(er) haben kein erkennbares Fehlerbeschreibungs-Muster (WCAG 3.3.1).".format(len(required_no_error)),
                "",
                "Implementiere aria-describedby mit Fehlermeldungen für Pflichtfelder.")

        # --- 3.3.2 Labels or Instructions (A) ---
        required_no_label = a11y.get("required_inputs_missing_label", [])
        for inp in required_no_label:
            add("wcag_A_21_332_required_no_label", "A", "2.1", "3.3.2", "understandable",
                "critical", "Pflichtfeld ohne Label",
                "Ein Pflichtfeld hat kein Label (WCAG 3.3.2).",
                str(inp)[:200],
                "Füge ein Label zu jedem Pflichtfeld hinzu.")

        placeholder_no_label = a11y.get("placeholder_only_no_label", [])
        for inp in placeholder_no_label:
            add("wcag_A_21_332_placeholder_no_label", "A", "2.1", "3.3.2", "understandable",
                "warning", "Placeholder ersetzt Label",
                "Ein Eingabefeld verwendet nur placeholder statt einem echten Label (WCAG 3.3.2).",
                str(inp)[:200],
                "Füge ein sichtbares <label> zusätzlich zum placeholder-Attribut hinzu.")

        # --- 3.3.3 Error Suggestion (AA) ---
        required_no_description = a11y.get("required_inputs_no_describedby", [])
        if required_no_description:
            add("wcag_AA_21_333_error_no_suggestion", "AA", "2.1", "3.3.3", "understandable",
                "info", "Pflichtfeld ohne Fehlervorschlag",
                "{} Pflichtfeld(er) haben kein aria-describedby mit Fehlerbeschreibung (WCAG 3.3.3).".format(len(required_no_description)),
                "",
                "Füge aria-describedby mit einem Fehlerhinweis-Element zu Pflichtfeldern hinzu.")

        # --- 3.3.4 Error Prevention (AA) ---
        forms_no_confirm = a11y.get("forms_no_confirm_mechanism", 0)
        if forms_no_confirm > 0:
            add("wcag_AA_21_334_no_error_prevention", "AA", "2.1", "3.3.4", "understandable",
                "info", "Formular ohne Bestätigungsschritt",
                "{} Formular(e) ohne erkennbaren Bestätigungs- oder Rückgängigmechanismus (WCAG 3.3.4).".format(forms_no_confirm),
                "",
                "Füge eine Bestätigungsseite oder Rückgängig-Funktion für wichtige Formulare hinzu.")

        # --- 3.3.5 Help (AAA) ---
        forms_no_help = a11y.get("forms_no_contextual_help", 0)
        if forms_no_help > 0:
            add("wcag_AAA_21_335_form_no_help", "AAA", "2.1", "3.3.5", "understandable",
                "info", "Formular ohne kontextbezogene Hilfe",
                "{} Formular(e) bieten keine kontextbezogene Hilfe (WCAG 3.3.5).".format(forms_no_help),
                "",
                "Füge Hilfetexte oder Tooltips zu komplexen Formularfeldern hinzu.")

        # --- 3.3.7 Redundant Entry (AA, WCAG 2.2) ---
        forms_no_autocomplete_recurring = a11y.get("forms_recurring_fields_no_autocomplete", 0)
        if forms_no_autocomplete_recurring > 0:
            add("wcag_AA_22_337_redundant_entry", "AA", "2.2", "3.3.7", "understandable",
                "info", "Wiederkehrende Felder ohne autocomplete",
                "Formularfelder die Informationen wiederholen haben kein autocomplete-Attribut (WCAG 3.3.7).",
                "",
                "Füge autocomplete-Attribute für wiederkehrende Eingabefelder hinzu.")

        # --- 3.1.3 Unusual Words (AAA) ---
        abbr_no_title = a11y.get("abbr_missing_title", [])
        for elem in abbr_no_title:
            add("wcag_AAA_21_314_abbr_no_title", "AAA", "2.1", "3.1.4", "understandable",
                "info", "Abkürzung ohne title-Attribut",
                "Ein <abbr>-Element hat kein title-Attribut zur Erklärung (WCAG 3.1.4).",
                elem[:200],
                "Füge title='Ausgeschriebene Abkürzung' zu jedem <abbr>-Element hinzu.")

        # ================================================================
        # ROBUST
        # ================================================================

        # --- 4.1.1 Parsing (A) ---
        dup_ids = a11y.get("duplicate_ids", [])
        for id_val in dup_ids:
            add("wcag_A_21_411_duplicate_id", "A", "2.1", "4.1.1", "robust",
                "warning", "Doppelte ID auf der Seite",
                "Die ID '{}' kommt mehrfach auf der Seite vor (WCAG 4.1.1).".format(id_val),
                "id='{}'".format(id_val),
                "Stelle sicher, dass alle HTML-IDs auf der Seite eindeutig sind.")

        # --- 4.1.2 Name, Role, Value (A) ---
        buttons_no_label = a11y.get("buttons_missing_label", [])
        for b in buttons_no_label:
            add("wcag_A_21_412_button_no_label", "A", "2.1", "4.1.2", "robust",
                "critical", "Button ohne barrierefreien Text",
                "Ein <button>-Element hat keinen sichtbaren Text und kein aria-label (WCAG 4.1.2).",
                "<button type='{}'></button>".format(b if isinstance(b, str) else "button"),
                "Füge sichtbaren Text oder aria-label zu allen Buttons hinzu.")

        inputs_no_name_id = a11y.get("inputs_missing_name_and_id", [])
        for elem in inputs_no_name_id:
            add("wcag_A_21_412_input_no_name_id", "A", "2.1", "4.1.2", "robust",
                "warning", "Eingabefeld ohne name und ohne id",
                "Ein Eingabefeld hat weder name noch id (WCAG 4.1.2).",
                elem[:200],
                "Füge id und name zu allen Eingabefeldern hinzu.")

        div_role_button_no_tab = a11y.get("div_role_button_no_tabindex", [])
        for elem in div_role_button_no_tab:
            add("wcag_A_21_412_div_button_no_tabindex", "A", "2.1", "4.1.2", "robust",
                "warning", "div/span mit role=button ohne tabindex",
                "Ein <div> oder <span> mit role='button' hat kein tabindex und ist per Tastatur nicht erreichbar (WCAG 4.1.2).",
                elem[:200],
                "Füge tabindex='0' zu allen Elementen mit role='button' hinzu.")

        a_no_href_no_role = a11y.get("anchor_no_href_no_role", [])
        for elem in a_no_href_no_role:
            add("wcag_A_21_412_anchor_no_href_no_role", "A", "2.1", "4.1.2", "robust",
                "warning", "<a> ohne href und ohne role",
                "Ein <a>-Element hat weder href noch role='button' und ist für Screenreader unklar (WCAG 4.1.2).",
                elem[:200],
                "Füge href oder role='button' mit tabindex zum Anker-Element hinzu.")

        # --- 4.1.3 Status Messages (AA, WCAG 2.1) ---
        live_regions_no_aria = a11y.get("live_regions_no_aria_live", [])
        for elem in live_regions_no_aria:
            add("wcag_AA_21_413_live_region_no_aria", "AA", "2.1", "4.1.3", "robust",
                "warning", "Live-Region ohne aria-live",
                "Ein Element mit role=alert/status hat kein aria-live-Attribut (WCAG 4.1.3).",
                elem[:200],
                "Füge aria-live='polite' oder aria-live='assertive' zur Status-Region hinzu.")

        # ================================================================
        # BFSG-specific (German Accessibility Strengthening Act)
        # ================================================================
        if not a11y.get("has_contact_link"):
            add("bfsg_missing_contact", "AA", "2.1", "BFSG", "understandable",
                "info", "Kein Kontaktlink (BFSG)",
                "Keine Kontaktinformationen (tel: oder mailto:) auf der Seite gefunden (BFSG).",
                "",
                "Füge Kontaktinformationen (Telefon oder E-Mail) auf jeder Seite ein.")

        if not a11y.get("has_impressum_link"):
            add("bfsg_missing_impressum", "AA", "2.1", "BFSG", "understandable",
                "info", "Kein Impressum-Link (BFSG/TMG)",
                "Kein sichtbarer Impressum-Link auf der Seite gefunden (BFSG/TMG).",
                "",
                "Füge einen sichtbaren Link zum Impressum auf jeder Seite ein.")

        if not a11y.get("has_accessibility_statement"):
            add("bfsg_missing_a11y_statement", "AA", "2.1", "BFSG", "understandable",
                "info", "Keine Barrierefreiheitserklärung (BFSG §12)",
                "Kein Link zur Barrierefreiheitserklärung auf der Seite (Pflicht ab 28.06.2025, BFSG §12).",
                "",
                "Veröffentliche eine Barrierefreiheitserklärung und verlinke sie auf jeder Seite.")

        return issues

    # ------------------------------------------------------------------
    # Feature 5: Keyword Analysis
    # ------------------------------------------------------------------
    def analyze_keywords(self, page: Dict[str, Any]) -> Dict[str, Any]:
        extra = page.get("extra_data") or {}
        body_text = extra.get("body_text", "") or ""
        word_count = page.get("word_count", 0) or 0

        if not body_text or word_count < 50:
            return {"top_keywords": [], "total_words": word_count, "keyword_density": {}}

        words = re.findall(r"\b[a-zA-ZäöüÄÖÜß]{3,}\b", body_text.lower())
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
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        filtered = [w for w in words if w not in self.STOPWORDS]
        if not filtered:
            return []
        counter = Counter(filtered)
        return counter.most_common(top_n)
