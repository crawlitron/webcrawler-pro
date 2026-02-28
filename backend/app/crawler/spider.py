
import re
import json
import scrapy
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse, urljoin
from typing import Optional, Callable


class SEOSpider(scrapy.Spider):
    name = "seo_spider"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 8,
        "DOWNLOAD_DELAY": 0.1,
        "COOKIES_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
        "LOG_ENABLED": False,
        "REDIRECT_ENABLED": True,
        "REDIRECT_MAX_TIMES": 5,
        "HTTPERROR_ALLOW_ALL": True,
        "USER_AGENT": "WebCrawlerPro/2.0 (+https://webcrawlerpro.io/bot)",
        "DOWNLOAD_TIMEOUT": 15,
        "DEPTH_LIMIT": 10,
    }

    def __init__(self, start_url: str, max_urls: int = 500,
                 page_callback: Optional[Callable] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_url = start_url
        self.max_urls = max_urls
        self.page_callback = page_callback
        self.crawled_count = 0
        self.visited_urls = set()
        parsed = urlparse(start_url)
        self.base_domain = parsed.netloc
        self.start_urls = [start_url]
        self.link_extractor = LinkExtractor(
            allow_domains=[self.base_domain],
            deny_extensions=[
                "pdf", "jpg", "jpeg", "png", "gif", "svg", "ico", "css", "js",
                "zip", "tar", "gz", "mp3", "mp4", "avi", "mov", "doc", "docx",
                "xls", "xlsx", "ppt", "pptx", "exe", "dmg", "woff", "woff2", "ttf",
            ],
        )

    def parse(self, response):
        if self.crawled_count >= self.max_urls:
            return
        url = response.url
        if url in self.visited_urls:
            return
        self.visited_urls.add(url)
        self.crawled_count += 1

        data = self._extract(response)
        if self.page_callback:
            self.page_callback(data)
        yield data

        ct = response.headers.get("Content-Type", b"").decode("utf-8", errors="ignore")
        if response.status == 200 and "text/html" in ct and self.crawled_count < self.max_urls:
            for link in self.link_extractor.extract_links(response):
                if link.url not in self.visited_urls:
                    yield scrapy.Request(
                        link.url, callback=self.parse, errback=self.errback,
                        meta={"depth": response.meta.get("depth", 0) + 1},
                    )

    def errback(self, failure):
        url = failure.request.url
        if url not in self.visited_urls:
            self.visited_urls.add(url)
            self.crawled_count += 1
            data = {
                "url": url, "status_code": None, "content_type": None,
                "response_time": None, "title": None, "meta_description": None,
                "h1": None, "h1_count": 0, "h2_count": 0, "canonical_url": None,
                "internal_links_count": 0, "external_links_count": 0,
                "images_without_alt": 0, "word_count": 0,
                "is_indexable": False, "redirect_url": None,
                "depth": failure.request.meta.get("depth", 0),
                "error": str(failure.value),
                "extra_data": {},
            }
            if self.page_callback:
                self.page_callback(data)
            yield data

    def _extract(self, response) -> dict:
        url = response.url
        status = response.status
        ct = response.headers.get(
            "Content-Type",
            b"").decode(
            "utf-8",
            errors="ignore").split(";")[0].strip()
        depth = response.meta.get("depth", 0)
        rt = response.meta.get("download_latency", 0.0)

        redirect_url = None
        if response.history:
            redirect_url = url

        title = meta_desc = h1 = canonical_url = None
        h1_count = h2_count = images_without_alt = word_count = 0
        internal_links = external_links = 0
        is_indexable = True
        extra_data = {}

        if "text/html" in ct and status == 200:
            # --- Title ---
            title_parts = response.css("title::text").getall()
            title = " ".join(title_parts).strip() or None

            # --- Meta description ---
            md = (response.css('meta[name="description"]::attr(content)').get()
                  or response.css('meta[name="Description"]::attr(content)').get())
            meta_desc = md.strip() if md else None

            # --- Headings ---
            h1_tags = response.css("h1")
            h1_count = len(h1_tags)
            h1_text = " ".join(h1_tags.css("::text").getall()).strip()
            h1 = h1_text or None
            h2_count = len(response.css("h2"))

            # --- Canonical ---
            canon = response.css('link[rel="canonical"]::attr(href)').get()
            if canon:
                canonical_url = urljoin(url, canon)

            # --- Robots meta ---
            robots_meta = response.css('meta[name="robots"]::attr(content)').get() or ""
            if "noindex" in robots_meta.lower():
                is_indexable = False

            # --- Open Graph ---
            og_title = response.css('meta[property="og:title"]::attr(content)').get()
            og_description = response.css('meta[property="og:description"]::attr(content)').get()
            og_image = response.css('meta[property="og:image"]::attr(content)').get()
            og_url = response.css('meta[property="og:url"]::attr(content)').get()
            og_type = response.css('meta[property="og:type"]::attr(content)').get()
            extra_data["og_title"] = og_title.strip() if og_title else None
            extra_data["og_description"] = og_description.strip() if og_description else None
            extra_data["og_image"] = og_image.strip() if og_image else None
            extra_data["og_url"] = og_url.strip() if og_url else None
            extra_data["og_type"] = og_type.strip() if og_type else None

            # --- Twitter Cards ---
            twitter_card = response.css('meta[name="twitter:card"]::attr(content)').get()
            twitter_title = response.css('meta[name="twitter:title"]::attr(content)').get()
            twitter_desc = response.css('meta[name="twitter:description"]::attr(content)').get()
            extra_data["twitter_card"] = twitter_card.strip() if twitter_card else None
            extra_data["twitter_title"] = twitter_title.strip() if twitter_title else None
            extra_data["twitter_description"] = twitter_desc.strip() if twitter_desc else None

            # --- JSON-LD / Schema.org structured data ---
            jsonld_scripts = response.css('script[type="application/ld+json"]::text').getall()
            has_jsonld = len(jsonld_scripts) > 0
            jsonld_types = []
            for script in jsonld_scripts:
                try:
                    data_parsed = json.loads(script.strip())
                    if isinstance(data_parsed, dict):
                        t = data_parsed.get("@type")
                        if t:
                            jsonld_types.append(t if isinstance(t, str) else str(t))
                    elif isinstance(data_parsed, list):
                        for item in data_parsed:
                            if isinstance(item, dict):
                                t = item.get("@type")
                                if t:
                                    jsonld_types.append(t if isinstance(t, str) else str(t))
                except (json.JSONDecodeError, ValueError):
                    pass
            has_schema_org = bool(response.css('[itemtype*="schema.org"]').get())
            extra_data["has_jsonld"] = has_jsonld
            extra_data["has_schema_org"] = has_schema_org
            extra_data["jsonld_types"] = jsonld_types

            # --- Links (internal + external with nofollow detection) ---
            base_netloc = urlparse(url).netloc
            internal_link_list = []
            external_link_list = []
            nofollow_count = 0
            for a in response.css("a[href]"):
                href = a.attrib.get("href", "").strip()
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                abs_url = urljoin(url, href)
                p = urlparse(abs_url)
                if p.scheme not in ("http", "https"):
                    continue
                rel = (a.attrib.get("rel") or "").lower()
                is_nofollow = "nofollow" in rel
                if is_nofollow:
                    nofollow_count += 1
                anchor_text = " ".join(a.css("::text").getall()).strip()[:200]
                link_info = {
                    "url": abs_url,
                    "text": anchor_text,
                    "nofollow": is_nofollow,
                }
                if p.netloc == base_netloc:
                    internal_links += 1
                    if len(internal_link_list) < 200:  # cap stored links
                        internal_link_list.append(link_info)
                else:
                    external_links += 1
                    if len(external_link_list) < 100:  # cap stored links
                        external_link_list.append(link_info)
            extra_data["internal_links"] = internal_link_list
            extra_data["external_links"] = external_link_list
            extra_data["nofollow_links_count"] = nofollow_count

            # --- Images (enhanced) ---
            total_images = 0
            images_without_alt = 0
            for img in response.css("img"):
                total_images += 1
                if not (img.attrib.get("alt") or "").strip():
                    images_without_alt += 1
            extra_data["total_images"] = total_images

            # --- Word count + body text for keyword density ---
            body_text = " ".join(response.css("body *::text").getall())
            word_count = len(re.findall(r"\b\w+\b", body_text))
            # Store trimmed body text (max 5000 chars) for keyword analysis
            extra_data["body_text"] = body_text[:5000] if body_text else ""

            # --- Page depth (from URL structure) ---
            url_path = urlparse(url).path
            url_depth = url_path.rstrip("/").count("/")
            extra_data["url_depth"] = url_depth

        return {
            "url": url,
            "status_code": status,
            "content_type": ct,
            "response_time": rt,
            "title": title,
            "meta_description": meta_desc,
            "h1": h1,
            "h1_count": h1_count,
            "h2_count": h2_count,
            "canonical_url": canonical_url,
            "internal_links_count": internal_links,
            "external_links_count": external_links,
            "images_without_alt": images_without_alt,
            "word_count": word_count,
            "is_indexable": is_indexable,
            "redirect_url": redirect_url,
            "depth": depth,
            "extra_data": extra_data,
        }
