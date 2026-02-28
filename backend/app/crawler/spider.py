
import re
import time
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
        "USER_AGENT": "WebCrawlerPro/1.0 (+https://webcrawlerpro.io/bot)",
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
                "pdf","jpg","jpeg","png","gif","svg","ico","css","js",
                "zip","tar","gz","mp3","mp4","avi","mov","doc","docx",
                "xls","xlsx","ppt","pptx","exe","dmg","woff","woff2","ttf",
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
            }
            if self.page_callback:
                self.page_callback(data)
            yield data

    def _extract(self, response) -> dict:
        url = response.url
        status = response.status
        ct = response.headers.get("Content-Type", b"").decode("utf-8", errors="ignore").split(";")[0].strip()
        depth = response.meta.get("depth", 0)
        rt = response.meta.get("download_latency", 0.0)

        redirect_url = None
        if response.history:
            redirect_url = url

        title = meta_desc = h1 = canonical_url = None
        h1_count = h2_count = images_without_alt = word_count = 0
        internal_links = external_links = 0
        is_indexable = True

        if "text/html" in ct and status == 200:
            title_parts = response.css("title::text").getall()
            title = " ".join(title_parts).strip() or None

            md = response.css('meta[name="description"]::attr(content)').get() or                  response.css('meta[name="Description"]::attr(content)').get()
            meta_desc = md.strip() if md else None

            h1_tags = response.css("h1")
            h1_count = len(h1_tags)
            h1_text = " ".join(h1_tags.css("::text").getall()).strip()
            h1 = h1_text or None
            h2_count = len(response.css("h2"))

            canon = response.css('link[rel="canonical"]::attr(href)').get()
            if canon:
                canonical_url = urljoin(url, canon)

            robots_meta = response.css('meta[name="robots"]::attr(content)').get() or ""
            if "noindex" in robots_meta.lower():
                is_indexable = False

            base_netloc = urlparse(url).netloc
            for href in response.css("a[href]::attr(href)").getall():
                abs_url = urljoin(url, href.strip())
                p = urlparse(abs_url)
                if p.scheme in ("http", "https"):
                    if p.netloc == base_netloc:
                        internal_links += 1
                    else:
                        external_links += 1

            for img in response.css("img"):
                if not (img.attrib.get("alt") or "").strip():
                    images_without_alt += 1

            body_text = " ".join(response.css("body *::text").getall())
            word_count = len(re.findall(r"\w+", body_text))

        return {
            "url": url, "status_code": status, "content_type": ct,
            "response_time": rt, "title": title, "meta_description": meta_desc,
            "h1": h1, "h1_count": h1_count, "h2_count": h2_count,
            "canonical_url": canonical_url, "internal_links_count": internal_links,
            "external_links_count": external_links, "images_without_alt": images_without_alt,
            "word_count": word_count, "is_indexable": is_indexable,
            "redirect_url": redirect_url, "depth": depth,
        }
