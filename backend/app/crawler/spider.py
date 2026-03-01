import re
import json
import scrapy
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse, urljoin
from typing import Optional, Callable, List


class SEOSpider(scrapy.Spider):
    name = "seo_spider"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 8,
        "COOKIES_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
        "LOG_ENABLED": False,
        "REDIRECT_ENABLED": True,
        "REDIRECT_MAX_TIMES": 10,
        "HTTPERROR_ALLOW_ALL": True,
        "DOWNLOAD_TIMEOUT": 15,
        "DEPTH_LIMIT": 10,
    }

    def __init__(
        self,
        start_url: str,
        max_urls: int = 500,
        page_callback: Optional[Callable] = None,
        custom_user_agent: Optional[str] = None,
        crawl_delay: float = 0.5,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        crawl_external_links: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.start_url = start_url
        self.max_urls = max_urls
        self.page_callback = page_callback
        self.crawl_delay = crawl_delay
        self.include_patterns = [re.compile(p) for p in (include_patterns or [])]
        self.exclude_patterns = [re.compile(p) for p in (exclude_patterns or [])]
        self.crawl_external_links = crawl_external_links

        ua = custom_user_agent or "WebCrawlerPro/2.0 (+https://webcrawlerpro.io/bot)"
        self.custom_settings = dict(self.custom_settings)
        self.custom_settings["USER_AGENT"] = ua
        self.custom_settings["DOWNLOAD_DELAY"] = crawl_delay

        self.crawled_count = 0
        self.visited_urls = set()
        parsed = urlparse(start_url)
        self.base_domain = parsed.netloc
        self.start_urls = [start_url]

        allowed_domains = None if crawl_external_links else [self.base_domain]
        self.link_extractor = LinkExtractor(
            allow_domains=allowed_domains,
            deny_extensions=[
                "pdf", "jpg", "jpeg", "png", "gif", "svg", "ico", "css", "js",
                "zip", "tar", "gz", "mp3", "mp4", "avi", "mov", "doc", "docx",
                "xls", "xlsx", "ppt", "pptx", "exe", "dmg", "woff", "woff2", "ttf",
            ],
        )

    def _url_allowed(self, url: str) -> bool:
        if self.exclude_patterns:
            for pat in self.exclude_patterns:
                if pat.search(url):
                    return False
        if self.include_patterns:
            for pat in self.include_patterns:
                if pat.search(url):
                    return True
            return False
        return True

    def parse(self, response):
        if self.crawled_count >= self.max_urls:
            return
        url = response.url
        if url in self.visited_urls:
            return
        if not self._url_allowed(url):
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
                if link.url not in self.visited_urls and self._url_allowed(link.url):
                    yield scrapy.Request(
                        link.url,
                        callback=self.parse,
                        errback=self.errback,
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
                "redirect_chain": [],
                "depth": failure.request.meta.get("depth", 0),
                "error": str(failure.value),
                "extra_data": {},
            }
            if self.page_callback:
                self.page_callback(data)
            yield data

    def _extract_redirect_chain(self, response) -> list:
        chain = []
        for r in response.history:
            chain.append({"url": r.url, "status_code": r.status})
        if response.history:
            chain.append({"url": response.url, "status_code": response.status})
        return chain

    def _extract_images(self, response, base_url: str) -> list:
        images = []
        for img in response.css("img"):
            src = img.attrib.get("src", "").strip()
            if not src:
                src = img.attrib.get("data-src", "").strip()
            abs_src = urljoin(base_url, src) if src else ""
            alt = img.attrib.get("alt", None)
            width = img.attrib.get("width", None)
            height = img.attrib.get("height", None)
            images.append({
                "src": abs_src,
                "alt": alt,
                "width": width,
                "height": height,
                "has_alt": alt is not None,
                "alt_empty": alt is not None and alt.strip() == "",
                "alt_too_long": alt is not None and len(alt) > 100,
                "missing_dimensions": width is None or height is None,
            })
        return images


    def _extract_accessibility(self, response, url: str, images_data: list) -> dict:
        """Extract accessibility data for WCAG 2.1 + 2.2 Level A/AA/AAA checks."""
        a11y = {}

        # --- lang attribute on <html> ---
        html_lang = response.css("html::attr(lang)").get() or ""
        html_lang = html_lang.strip()
        a11y["html_lang"] = html_lang
        a11y["html_lang_missing"] = html_lang == ""
        # Invalid if non-empty but not a valid 2-letter (or xx-XX) code
        lang_base = html_lang.split("-")[0].lower() if html_lang else ""
        VALID_LANGS = {
            "ab","aa","af","ak","sq","am","ar","an","hy","as","av","ae","ay","az",
            "bm","ba","eu","be","bn","bi","bs","br","bg","my","ca","ch","ce",
            "ny","zh","cv","kw","co","cr","hr","cs","da","nl","dz","en","eo",
            "et","ee","fo","fj","fi","fr","ff","gl","ka","de","el","gn","gu",
            "ha","he","hi","hu","ia","id","ie","ga","ig","io","is","it","ja",
            "jv","kl","kn","ks","kk","km","ki","rw","ky","kg","ko","ku","la",
            "lb","lg","li","ln","lo","lt","lu","lv","gv","mk","mg","ms","ml",
            "mt","mi","mr","mn","na","nv","nd","ne","nb","nn","no","oc","om",
            "or","pa","fa","pl","ps","pt","qu","rm","rn","ro","ru","sa","sc",
            "sd","se","sm","sg","sr","gd","sn","si","sk","sl","so","st","es",
            "su","sw","sv","ta","te","tg","th","ti","bo","tk","tl","tn","to",
            "tr","ts","tt","tw","ty","ug","uk","ur","uz","ve","vi","vo","wa",
            "cy","wo","fy","xh","yi","yo","za","zu",
        }
        a11y["html_lang_invalid"] = (html_lang != "" and lang_base not in VALID_LANGS)
        a11y["html_lang_short"] = (0 < len(html_lang) < 2)

        # --- viewport meta ---
        viewport_content = (
            response.css("meta[name='viewport']::attr(content)").get()
            or response.css('meta[name="viewport"]::attr(content)').get()
            or ""
        )
        a11y["viewport_content"] = viewport_content
        a11y["viewport_no_scale"] = "user-scalable=no" in viewport_content.lower()
        max_scale_match = re.search(r"maximum-scale=([\d.]+)", viewport_content)
        a11y["viewport_max_scale"] = float(max_scale_match.group(1)) if max_scale_match else None

        # --- WCAG 1.1.1: Images without alt ---
        a11y["images_missing_alt"] = [img["src"] for img in images_data if img["alt"] is None][:50]
        a11y["images_empty_alt_non_decorative"] = [
            img["src"] for img in images_data
            if img.get("alt_empty") and img.get("role") != "presentation"
        ][:50]

        # --- 1.1.1: input[type=image] without alt ---
        img_input_no_alt = []
        for inp in response.css("input[type=image]"):
            if not inp.attrib.get("alt"):
                src = inp.attrib.get("src", "")[:80]
                img_input_no_alt.append("<input type='image' src='{}' ...>".format(src))
        a11y["img_input_missing_alt"] = img_input_no_alt[:20]

        # --- 1.1.1: area without alt ---
        area_no_alt = []
        for area in response.css("area"):
            if not area.attrib.get("alt") and area.attrib.get("alt") is None:
                href = area.attrib.get("href", "")[:60]
                area_no_alt.append("<area href='{}'>".format(href))
        a11y["area_missing_alt"] = area_no_alt[:20]

        # --- 1.1.1: SVG without title or aria-label ---
        svg_no_name = []
        for svg in response.css("svg"):
            role = svg.attrib.get("role", "")
            aria_label = svg.attrib.get("aria-label", "")
            aria_hidden = svg.attrib.get("aria-hidden", "")
            has_title = bool(svg.css("title"))
            if not has_title and not aria_label and aria_hidden != "true" and role != "presentation":
                svg_no_name.append("<svg class='{}'>...".format(svg.attrib.get("class", "")[:40]))
        a11y["svg_missing_accessible_name"] = svg_no_name[:20]

        # --- 1.1.1: object/embed without text ---
        obj_no_text = []
        for obj in response.css("object, embed"):
            text = " ".join(obj.css("::text").getall()).strip()
            aria_label = obj.attrib.get("aria-label", "")
            if not text and not aria_label:
                tag = obj.root.tag
                obj_no_text.append("<{} ...>".format(tag))
        a11y["object_embed_no_text"] = obj_no_text[:10]

        # --- 1.2.x: Audio/Video checks ---
        audio_no_transcript = []
        audio_autoplay = []
        video_no_captions = []
        video_no_desc = []
        video_no_controls = []
        video_autoplay = []
        media_missing_captions = []

        for audio in response.css("audio"):
            src = audio.attrib.get("src", "") or audio.css("source::attr(src)").get() or ""
            elem_str = "<audio src='{}'>...".format(src[:60])
            tracks = audio.css("track")
            has_captions = any(t.attrib.get("kind", "") in ("captions", "subtitles") for t in tracks)
            has_desc_track = any(t.attrib.get("kind", "") == "descriptions" for t in tracks)
            has_describedby = bool(audio.attrib.get("aria-describedby"))
            if not has_captions and not has_desc_track and not has_describedby:
                audio_no_transcript.append(elem_str)
            if "autoplay" in audio.attrib:
                audio_autoplay.append(elem_str)
            if not has_captions:
                media_missing_captions.append({"tag": "audio", "src": src[:100]})

        for video in response.css("video"):
            src = video.attrib.get("src", "") or video.css("source::attr(src)").get() or ""
            elem_str = "<video src='{}'>...".format(src[:60])
            tracks = video.css("track")
            has_captions = any(t.attrib.get("kind", "") in ("captions", "subtitles") for t in tracks)
            has_desc = any(t.attrib.get("kind", "") == "descriptions" for t in tracks)
            if not has_captions:
                video_no_captions.append(elem_str)
                media_missing_captions.append({"tag": "video", "src": src[:100]})
            if not has_desc:
                video_no_desc.append(elem_str)
            if "controls" not in video.attrib:
                video_no_controls.append(elem_str)
            if "autoplay" in video.attrib:
                video_autoplay.append(elem_str)

        a11y["audio_missing_transcript_hint"] = audio_no_transcript[:10]
        a11y["audio_autoplay"] = audio_autoplay[:10]
        a11y["video_missing_captions"] = video_no_captions[:10]
        a11y["video_missing_audio_description"] = video_no_desc[:10]
        a11y["video_missing_controls"] = video_no_controls[:10]
        a11y["video_autoplay"] = video_autoplay[:10]
        a11y["media_missing_captions"] = media_missing_captions[:20]

        # --- 1.3.1 Form / table structure ---
        label_for_ids = set(response.css("label::attr(for)").getall())

        inputs_missing_label = []
        required_missing_label = []
        placeholder_only = []
        inputs_no_name_id = []
        required_no_error = []
        required_no_describedby = []
        skip_types = {"hidden", "submit", "button", "image", "reset"}
        for inp in response.css("input"):
            itype = inp.attrib.get("type", "text").lower()
            if itype in skip_types:
                continue
            iid = inp.attrib.get("id", "")
            iname = inp.attrib.get("name", "")
            aria_label = inp.attrib.get("aria-label", "")
            aria_labelledby = inp.attrib.get("aria-labelledby", "")
            title_attr = inp.attrib.get("title", "")
            placeholder = inp.attrib.get("placeholder", "")
            has_label = (iid and iid in label_for_ids) or aria_label or aria_labelledby or title_attr
            is_required = "required" in inp.attrib or inp.attrib.get("aria-required") == "true"
            elem_str = "<input type='{}' name='{}' id='{}' />".format(itype, iname, iid)
            if not has_label:
                inputs_missing_label.append({"type": itype, "name": iname})
                if is_required:
                    required_missing_label.append(elem_str)
            if placeholder and not has_label:
                placeholder_only.append(elem_str)
            if not iname and not iid:
                inputs_no_name_id.append(elem_str)
            if is_required and not inp.attrib.get("aria-describedby"):
                required_no_describedby.append(elem_str)
            if is_required and not has_label:
                required_no_error.append(elem_str)

        a11y["inputs_missing_label"] = inputs_missing_label[:30]
        a11y["required_inputs_missing_label"] = required_missing_label[:20]
        a11y["placeholder_only_no_label"] = placeholder_only[:20]
        a11y["inputs_missing_name_and_id"] = inputs_no_name_id[:20]
        a11y["required_inputs_no_error_pattern"] = required_no_error[:20]
        a11y["required_inputs_no_describedby"] = required_no_describedby[:20]

        # --- textarea without label ---
        textarea_no_label = []
        for ta in response.css("textarea"):
            ta_id = ta.attrib.get("id", "")
            aria_label = ta.attrib.get("aria-label", "")
            aria_labelledby = ta.attrib.get("aria-labelledby", "")
            if not ((ta_id and ta_id in label_for_ids) or aria_label or aria_labelledby):
                textarea_no_label.append("<textarea name='{}'>...".format(ta.attrib.get("name", "")[:30]))
        a11y["textarea_missing_label"] = textarea_no_label[:20]

        # --- fieldset without legend ---
        fieldset_no_legend = []
        for fs in response.css("fieldset"):
            if not fs.css("legend"):
                fieldset_no_legend.append("<fieldset>...")
        a11y["fieldset_missing_legend"] = fieldset_no_legend[:10]

        # --- Tables ---
        tables_no_th = []
        tables_no_caption = []
        th_no_scope = []
        layout_tables = []
        for table in response.css("table"):
            has_th = bool(table.css("th"))
            has_caption = bool(table.css("caption")) or bool(table.attrib.get("aria-label"))
            is_layout = bool(table.attrib.get("role") == "presentation" or table.attrib.get("role") == "none")
            if not is_layout:
                if not has_th:
                    tables_no_th.append("<table>...")
                if not has_caption:
                    tables_no_caption.append("<table>...")
                for th in table.css("th"):
                    if not th.attrib.get("scope"):
                        siblings = table.css("th")
                        if len(siblings) > 2:
                            th_no_scope.append("<th>{}</th>".format(" ".join(th.css("::text").getall())[:30]))
            else:
                layout_tables.append("<table role='presentation'>")
        a11y["tables_missing_th"] = tables_no_th[:10]
        a11y["tables_missing_caption"] = tables_no_caption[:10]
        a11y["th_missing_scope"] = th_no_scope[:20]
        a11y["layout_tables"] = layout_tables[:10]

        # --- select without label ---
        select_missing_label = []
        for sel in response.css("select"):
            sel_id = sel.attrib.get("id", "")
            aria_label = sel.attrib.get("aria-label", "")
            aria_labelledby = sel.attrib.get("aria-labelledby", "")
            has_label = (sel_id and sel_id in label_for_ids) or aria_label or aria_labelledby
            if not has_label:
                select_missing_label.append(sel.attrib.get("name", ""))
        a11y["select_missing_label"] = select_missing_label[:20]

        # --- buttons without label ---
        buttons_missing_label = []
        for btn in response.css("button"):
            text = " ".join(btn.css("::text").getall()).strip()
            aria_label = btn.attrib.get("aria-label", "")
            aria_labelledby = btn.attrib.get("aria-labelledby", "")
            title_attr = btn.attrib.get("title", "")
            if not text and not aria_label and not aria_labelledby and not title_attr:
                buttons_missing_label.append(btn.attrib.get("type", "button"))
        a11y["buttons_missing_label"] = buttons_missing_label[:30]

        # --- div/span with role=button no tabindex ---
        div_btn_no_tab = []
        for el in response.css("[role=button]"):
            tag = el.root.tag
            if tag not in ("button", "a", "input") and "tabindex" not in el.attrib:
                text = " ".join(el.css("::text").getall()).strip()[:40]
                div_btn_no_tab.append("<{} role='button'>{}</{}>" .format(tag, text, tag))
        a11y["div_role_button_no_tabindex"] = div_btn_no_tab[:20]

        # --- anchor no href no role ---
        anchor_no_href_no_role = []
        for a_el in response.css("a"):
            href = a_el.attrib.get("href", "")
            role = a_el.attrib.get("role", "")
            if not href and not role:
                text = " ".join(a_el.css("::text").getall()).strip()[:40]
                anchor_no_href_no_role.append("<a>{}</a>".format(text))
        a11y["anchor_no_href_no_role"] = anchor_no_href_no_role[:20]

        # --- Duplicate IDs ---
        all_ids = response.css("[id]::attr(id)").getall()
        seen = set()
        dup_ids = set()
        for id_val in all_ids:
            if id_val in seen:
                dup_ids.add(id_val)
            seen.add(id_val)
        a11y["duplicate_ids"] = list(dup_ids)[:30]

        # --- Links analysis ---
        vague_texts = {
            "hier klicken","hier","mehr","weiter","read more","click here",
            "more","next","link","klick hier","details","jetzt","here",
            "lesen","weiterleiten","learn more","see more","view more",
        }
        empty_links = []
        vague_links = []
        icon_links_no_aria = []
        blank_links_no_warn = []
        skip_nav_found = False

        for a_el in response.css("a"):
            href = a_el.attrib.get("href", "").strip()
            text = " ".join(a_el.css("::text").getall()).strip()
            aria_label = a_el.attrib.get("aria-label", "").strip()
            target = a_el.attrib.get("target", "")
            rel = a_el.attrib.get("rel", "").lower()

            if href.startswith("#") and (
                "skip" in text.lower() or "zum inhalt" in text.lower()
                or "zum hauptinhalt" in text.lower() or "skip" in href.lower()
            ):
                skip_nav_found = True

            if not text and not aria_label:
                icon_classes = " ".join(a_el.css("[class]::attr(class)").getall())
                if any(x in icon_classes for x in ["icon","fa-","bi-","glyphicon","material-icons"]):
                    icon_links_no_aria.append(href[:100])
                elif href and not href.startswith("javascript"):
                    empty_links.append(href[:100])
            elif text.lower() in vague_texts:
                vague_links.append({"text": text, "href": href[:100]})

            if target == "_blank" and "noopener" not in rel:
                has_warning_text = any(
                    w in text.lower() for w in ["neues fenster","new window","new tab","neuer tab","(external)"]
                )
                has_warning_title = any(
                    w in a_el.attrib.get("title", "").lower()
                    for w in ["neues fenster","new window","new tab"]
                )
                if not has_warning_text and not has_warning_title:
                    blank_links_no_warn.append("<a href='{}' target='_blank'>{}...</".format(href[:60], text[:30]))

        a11y["empty_links"] = empty_links[:30]
        a11y["vague_links"] = vague_links[:30]
        a11y["icon_links_no_aria"] = icon_links_no_aria[:30]
        a11y["skip_nav_found"] = skip_nav_found
        a11y["links_target_blank_no_warning"] = blank_links_no_warn[:20]

        # --- tabindex > 0 ---
        positive_tabindex = []
        for el in response.css("[tabindex]"):
            try:
                val = int(el.attrib.get("tabindex", 0))
                if val > 0:
                    positive_tabindex.append({"tag": el.root.tag, "tabindex": val})
            except (ValueError, TypeError):
                pass
        a11y["positive_tabindex"] = positive_tabindex[:20]

        # --- Landmark regions ---
        landmarks_missing = []
        if not response.css("main, [role=main]"):
            landmarks_missing.append("main")
        if not response.css("nav, [role=navigation]"):
            landmarks_missing.append("nav")
        if not response.css("header, [role=banner]"):
            landmarks_missing.append("header")
        if not response.css("footer, [role=contentinfo]"):
            landmarks_missing.append("footer")
        a11y["landmark_regions_missing"] = landmarks_missing

        # --- Heading hierarchy ---
        empty_headings = []
        heading_levels = []
        for level in range(1, 7):
            for h in response.css("h{}".format(level)):
                text = " ".join(h.css("::text").getall()).strip()
                if not text:
                    empty_headings.append("<h{}>...</h{}>".format(level, level))
                else:
                    heading_levels.append(level)
        a11y["empty_headings"] = empty_headings[:20]

        heading_skips = []
        for i in range(len(heading_levels) - 1):
            current = heading_levels[i]
            next_h = heading_levels[i + 1]
            if next_h > current + 1:
                heading_skips.append({"from": "h{}".format(current), "to": "h{}".format(next_h)})
        a11y["heading_hierarchy_skip"] = heading_skips[:10]

        # --- Sections without headings ---
        sections_no_heading = 0
        for section in response.css("section, article"):
            has_heading = bool(section.css("h1,h2,h3,h4,h5,h6"))
            if not has_heading:
                sections_no_heading += 1
        a11y["sections_without_headings"] = sections_no_heading

        # --- 2.2.1: meta refresh ---
        meta_refresh = []
        for meta in response.css("meta[http-equiv]"):
            if meta.attrib.get("http-equiv", "").lower() == "refresh":
                meta_refresh.append("<meta http-equiv='refresh' content='{}'>"                     .format(meta.attrib.get("content", "")[:60]))
        a11y["meta_refresh"] = meta_refresh[:5]

        # --- 2.2.2: marquee/blink ---
        marquee_blink = []
        for el in response.css("marquee, blink"):
            text = " ".join(el.css("::text").getall()).strip()[:50]
            marquee_blink.append("<{}>{}</{}>".format(el.root.tag, text, el.root.tag))
        a11y["marquee_blink"] = marquee_blink[:10]

        # --- 2.1.1: onclick on non-focusable elements ---
        onclick_nonfocusable = []
        focusable_tags = {"a","button","input","select","textarea","details","summary"}
        for el in response.css("[onclick]"):
            tag = el.root.tag
            tabindex = el.attrib.get("tabindex")
            role = el.attrib.get("role", "")
            if tag not in focusable_tags and tabindex is None and role not in ("button","link","menuitem"):
                onclick_nonfocusable.append(
                    "<{} onclick='...'>{}</{}>".format(
                        tag, " ".join(el.css("::text").getall()).strip()[:30], tag
                    )
                )
        a11y["onclick_nonfocusable"] = onclick_nonfocusable[:20]

        # --- 2.1.1: onmouseover without onfocus ---
        mouseover_no_focus = []
        for el in response.css("[onmouseover]"):
            if "onfocus" not in el.attrib:
                tag = el.root.tag
                mouseover_no_focus.append(
                    "<{} onmouseover='...'>{}</{}>".format(
                        tag, " ".join(el.css("::text").getall()).strip()[:30], tag
                    )
                )
        a11y["onmouseover_no_onfocus"] = mouseover_no_focus[:20]

        # --- 2.1.1: ondblclick ---
        ondblclick_elems = []
        for el in response.css("[ondblclick]"):
            tag = el.root.tag
            ondblclick_elems.append("<{} ondblclick='...'>".format(tag))
        a11y["ondblclick_elements"] = ondblclick_elems[:10]

        # --- 2.1.3: draggable without keyboard handler ---
        draggable_no_kb = []
        for el in response.css("[draggable=true], [draggable]"):
            draggable_val = el.attrib.get("draggable", "").lower()
            if draggable_val in ("true", ""):
                has_kb = "onkeydown" in el.attrib or "onkeyup" in el.attrib or "onkeypress" in el.attrib
                if not has_kb:
                    tag = el.root.tag
                    draggable_no_kb.append("<{} draggable='true'>".format(tag))
        a11y["draggable_no_keyboard"] = draggable_no_kb[:10]

        # --- 3.1.x: onfocus/onchange navigation ---
        onfocus_nav = []
        for el in response.css("[onfocus]"):
            handler = el.attrib.get("onfocus", "").lower()
            if "location" in handler or "href" in handler or "submit" in handler:
                onfocus_nav.append(
                    "<{} onfocus='{}' />".format(el.root.tag, el.attrib.get("onfocus", "")[:60])
                )
        a11y["onfocus_navigation"] = onfocus_nav[:10]

        onchange_nav = []
        for sel_el in response.css("select[onchange]"):
            handler = sel_el.attrib.get("onchange", "").lower()
            if "location" in handler or "href" in handler or "window" in handler:
                onchange_nav.append(
                    "<select onchange='{}' name='{}' />".format(
                        sel_el.attrib.get("onchange", "")[:60], sel_el.attrib.get("name", "")[:30]
                    )
                )
        a11y["onchange_navigation"] = onchange_nav[:10]

        # --- autocomplete missing ---
        inputs_no_autocomplete = []
        name_patterns = re.compile(
            r"(name|email|phone|tel|address|city|zip|postal|firstname|lastname|givenname|familyname)",
            re.IGNORECASE
        )
        for inp in response.css("input"):
            itype = inp.attrib.get("type", "text").lower()
            iname = inp.attrib.get("name", "") or ""
            has_autocomplete = "autocomplete" in inp.attrib
            if has_autocomplete:
                continue
            if itype in ("email", "tel"):
                inputs_no_autocomplete.append({"type": itype, "name": iname})
            elif itype == "text" and name_patterns.search(iname):
                inputs_no_autocomplete.append({"type": itype, "name": iname})
        a11y["inputs_missing_autocomplete"] = inputs_no_autocomplete[:20]

        # --- Inline style contrast checks ---
        contrast_issues = []
        contrast_aaa_issues = []
        color_re = re.compile(r"color:\s*([^;]+)", re.IGNORECASE)
        bg_re = re.compile(r"background(?:-color)?:\s*([^;]+)", re.IGNORECASE)
        font_size_re = re.compile(r"font-size:\s*([\d.]+)px", re.IGNORECASE)
        for el in response.css("[style]"):
            style = el.attrib.get("style", "")
            color_m = color_re.search(style)
            bg_m = bg_re.search(style)
            if color_m and bg_m:
                from urllib.parse import urlparse as _up
                def _css_to_hex(val):
                    val = val.strip().lower()
                    named = {
                        "black":"#000000","white":"#ffffff","red":"#ff0000",
                        "green":"#008000","blue":"#0000ff","yellow":"#ffff00",
                        "gray":"#808080","grey":"#808080","silver":"#c0c0c0",
                        "navy":"#000080","teal":"#008080","purple":"#800080",
                        "orange":"#ffa500","lime":"#00ff00","aqua":"#00ffff",
                    }
                    if val in named: return named[val]
                    if val.startswith("#"): return val
                    m = re.match(r"rgb\((\d+),(\d+),(\d+)\)", val.replace(" ",""))
                    if m: return "#{:02x}{:02x}{:02x}".format(int(m.group(1)),int(m.group(2)),int(m.group(3)))
                    return None
                def _contrast(h1, h2):
                    def _lum(h):
                        h = h.lstrip("#")
                        if len(h)==3: h=h[0]*2+h[1]*2+h[2]*2
                        if len(h)!=6: return None
                        try:
                            r,g,b = int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255
                            def _ch(v): return v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4
                            return 0.2126*_ch(r)+0.7152*_ch(g)+0.0722*_ch(b)
                        except: return None
                    l1,l2=_lum(h1),_lum(h2)
                    if l1 is None or l2 is None: return None
                    lighter,darker=max(l1,l2),min(l1,l2)
                    return (lighter+0.05)/(darker+0.05)
                fg = _css_to_hex(color_m.group(1))
                bg = _css_to_hex(bg_m.group(1))
                if fg and bg and fg != "transparent" and bg != "transparent":
                    ratio = _contrast(fg, bg)
                    if ratio is not None:
                        fsm = font_size_re.search(style)
                        font_px = float(fsm.group(1)) if fsm else 16
                        threshold = 3.0 if font_px >= 18 else 4.5
                        tag = el.root.tag
                        text_snippet = " ".join(el.css("::text").getall()).strip()[:40]
                        elem_str = "<{} style='{}'>{}".format(tag, style[:60], text_snippet)
                        if ratio < threshold:
                            contrast_issues.append({"ratio": round(ratio,2), "element": elem_str[:200]})
                        if ratio < 7.0:
                            contrast_aaa_issues.append({"ratio": round(ratio,2), "element": elem_str[:200]})
        a11y["contrast_issues"] = contrast_issues[:20]
        a11y["contrast_aaa_issues"] = contrast_aaa_issues[:20]

        # --- Inline px font count ---
        px_font_count = 0
        for el in response.css("[style]"):
            if font_size_re.search(el.attrib.get("style", "")):
                px_font_count += 1
        a11y["inline_px_font_count"] = px_font_count

        # --- Justified text ---
        justified_count = 0
        for el in response.css("[style]"):
            style = el.attrib.get("style", "").lower()
            if "text-align:justify" in style.replace(" ","") or "text-align: justify" in style:
                justified_count += 1
        a11y["justified_text_count"] = justified_count

        # --- Text spacing !important ---
        text_spacing_important = []
        for style_tag in response.css("style::text").getall():
            if "!important" in style_tag and any(
                p in style_tag for p in ["line-height","letter-spacing","word-spacing"]
            ):
                text_spacing_important.append("<style>...!important on text spacing...")
                break
        for el in response.css("[style]"):
            style = el.attrib.get("style", "").lower()
            if "!important" in style and any(
                p in style for p in ["line-height","letter-spacing","word-spacing"]
            ):
                tag = el.root.tag
                text_spacing_important.append("<{} style='{}' />".format(tag, style[:60]))
        a11y["text_spacing_important"] = text_spacing_important[:10]

        # --- title attribute as primary info ---
        title_as_primary = []
        for el in response.css("[title]"):
            tag = el.root.tag
            if tag in ("abbr", "acronym"):
                continue
            text = " ".join(el.css("::text").getall()).strip()
            aria_label = el.attrib.get("aria-label", "")
            if not text and not aria_label:
                title_attr = el.attrib.get("title", "")[:60]
                title_as_primary.append("<{} title='{}' />".format(tag, title_attr))
        a11y["title_as_primary_info"] = title_as_primary[:10]

        # --- reflow: fixed width in inline styles ---
        reflow_fixed = []
        width_px_re = re.compile(r"width:\s*\d+px", re.IGNORECASE)
        for el in response.css("[style]"):
            style = el.attrib.get("style", "")
            if width_px_re.search(style):
                overflow = "overflow" in style.lower()
                if overflow or el.root.tag == "body":
                    reflow_fixed.append("<{} style='{}'>".format(el.root.tag, style[:60]))
        a11y["reflow_fixed_width"] = reflow_fixed[:10]

        # --- outline:none in inline styles ---
        outline_none = []
        for el in response.css("[style]"):
            style = el.attrib.get("style", "").lower()
            if "outline:none" in style.replace(" ","") or "outline: none" in style:
                tag = el.root.tag
                outline_none.append("<{} style='{}'>".format(tag, el.attrib.get("style","")[:60]))
        a11y["outline_none_no_alternative"] = outline_none[:10]

        # --- links without underline ---
        links_no_underline = []
        for a_el in response.css("a[style]"):
            style = a_el.attrib.get("style", "").lower()
            aria_role = a_el.attrib.get("role", "")
            if ("text-decoration:none" in style.replace(" ","") or
                    "text-decoration: none" in style):
                if not aria_role:
                    href = a_el.attrib.get("href", "")[:60]
                    links_no_underline.append("<a href='{}' style='{}'>".format(href, style[:40]))
        a11y["links_no_underline_no_aria"] = links_no_underline[:10]

        # --- live regions ---
        live_no_aria = []
        for el in response.css("[role=alert], [role=status], [role=log], [role=marquee], [role=timer]"):
            if "aria-live" not in el.attrib:
                tag = el.root.tag
                live_no_aria.append("<{} role='{}' />".format(tag, el.attrib.get("role", "")))
        a11y["live_regions_no_aria_live"] = live_no_aria[:10]

        # --- abbr without title ---
        abbr_no_title = []
        for abbr in response.css("abbr"):
            if not abbr.attrib.get("title"):
                text = " ".join(abbr.css("::text").getall()).strip()[:30]
                abbr_no_title.append("<abbr>{}</abbr>".format(text))
        a11y["abbr_missing_title"] = abbr_no_title[:20]

        # --- label in name mismatch ---
        label_mismatch = []
        for el in response.css("[aria-label]"):
            tag = el.root.tag
            aria_label = el.attrib.get("aria-label", "").strip().lower()
            visible_text = " ".join(el.css("::text").getall()).strip().lower()
            if visible_text and aria_label and visible_text not in aria_label and aria_label not in visible_text:
                label_mismatch.append({"visible": visible_text[:40], "aria": aria_label[:40]})
        a11y["label_in_name_mismatch"] = label_mismatch[:10]

        # --- auto-refresh (meta refresh with interval > 0) ---
        auto_refresh_no_ctrl = []
        for meta in response.css("meta[http-equiv]"):
            if meta.attrib.get("http-equiv","").lower() == "refresh":
                content = meta.attrib.get("content","")
                try:
                    interval = int(content.split(";")[0].strip())
                    if interval > 0:
                        auto_refresh_no_ctrl.append("<meta http-equiv='refresh' content='{}'>".format(content[:60]))
                except (ValueError, IndexError):
                    pass
        a11y["auto_refresh_no_control"] = auto_refresh_no_ctrl[:5]

        # --- orientation lock detection ---
        orientation_locked = False
        for style_text in response.css("style::text").getall():
            if "orientation" in style_text and "portrait" in style_text:
                orientation_locked = True
                break
        a11y["orientation_locked"] = orientation_locked

        # --- sticky header without scroll-padding ---
        sticky_no_scroll_padding = False
        for style_text in response.css("style::text").getall():
            if "position:sticky" in style_text.replace(" ","") or "position: sticky" in style_text:
                if "scroll-padding" not in style_text:
                    sticky_no_scroll_padding = True
                    break
        for el in response.css("[style]"):
            if "position:sticky" in el.attrib.get("style","").replace(" ",""):
                sticky_no_scroll_padding = True
                break
        a11y["sticky_header_no_scroll_padding"] = sticky_no_scroll_padding

        # --- forms: confirm mechanism, help, autocomplete recurring ---
        forms_no_confirm = 0
        forms_no_help = 0
        forms_recurring_no_ac = 0
        for form in response.css("form"):
            has_confirm = bool(form.css("[type=reset], [data-confirm], [data-modal]"))
            if not has_confirm:
                forms_no_confirm += 1
            has_help = bool(form.css("[aria-describedby], .help-text, .hint, .form-hint"))
            if not has_help:
                forms_no_help += 1
            inputs_in_form = form.css("input:not([type=hidden]):not([type=submit]):not([type=button])")
            if len(inputs_in_form) > 3:
                missing_ac = sum(
                    1 for i in inputs_in_form if "autocomplete" not in i.attrib
                )
                if missing_ac > 1:
                    forms_recurring_no_ac += 1
        a11y["forms_no_confirm_mechanism"] = forms_no_confirm
        a11y["forms_no_contextual_help"] = forms_no_help
        a11y["forms_recurring_fields_no_autocomplete"] = forms_recurring_no_ac

        # --- required inputs ---
        a11y["required_inputs_no_error_pattern"] = required_no_error[:20]

        # --- BFSG checks ---
        all_hrefs = response.css("a::attr(href)").getall()
        all_link_texts = [
            " ".join(a_el.css("::text").getall()).strip().lower()
            for a_el in response.css("a")
        ]

        has_contact = any("tel:" in h or "mailto:" in h for h in all_hrefs)
        a11y["has_contact_link"] = has_contact

        has_impressum = any(
            "impressum" in h.lower() or "imprint" in h.lower() for h in all_hrefs
        ) or any("impressum" in t or "imprint" in t for t in all_link_texts)
        a11y["has_impressum_link"] = has_impressum

        has_a11y_statement = any(
            "barriere" in h.lower() or "accessibility" in h.lower()
            or "barrierefreiheit" in h.lower() for h in all_hrefs
        ) or any(
            "barriere" in t or "accessibility" in t or "barrierefreiheit" in t
            for t in all_link_texts
        )
        a11y["has_accessibility_statement"] = has_a11y_statement

        has_search = bool(
            response.css("[role=search], [type=search], input[name*=search], input[name*=suche]")
        )
        a11y["has_search"] = has_search

        has_sitemap = any(
            "sitemap" in h.lower() for h in all_hrefs
        ) or any("sitemap" in t for t in all_link_texts)
        a11y["has_sitemap_link"] = has_sitemap

        has_breadcrumb = bool(
            response.css("[aria-label*=breadcrumb], [aria-label*=Breadcrumb], "
                         "nav.breadcrumb, .breadcrumb, [class*=breadcrumb]")
        ) or any("breadcrumb" in t or "brotkrumen" in t for t in all_link_texts)
        a11y["has_breadcrumb"] = has_breadcrumb

        has_help = any(
            t in ["hilfe","help","faq","support","kontakt","contact"]
            for t in all_link_texts
        ) or any(
            "hilfe" in h.lower() or "/help" in h.lower() or "/faq" in h.lower()
            for h in all_hrefs
        )
        a11y["has_help_link"] = has_help

        return a11y

    def _extract(self, response) -> dict:
        url = response.url
        status = response.status
        ct = response.headers.get(
            "Content-Type", b""
        ).decode("utf-8", errors="ignore").split(";")[0].strip()
        depth = response.meta.get("depth", 0)
        rt = response.meta.get("download_latency", 0.0)

        redirect_chain = self._extract_redirect_chain(response)
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

            # --- JSON-LD / Schema.org ---
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

            # --- Links ---
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
                link_info = {"url": abs_url, "text": anchor_text, "nofollow": is_nofollow}
                if p.netloc == base_netloc:
                    internal_links += 1
                    if len(internal_link_list) < 200:
                        internal_link_list.append(link_info)
                else:
                    external_links += 1
                    if len(external_link_list) < 100:
                        external_link_list.append(link_info)
            extra_data["internal_links"] = internal_link_list
            extra_data["external_links"] = external_link_list
            extra_data["nofollow_links_count"] = nofollow_count

            # --- Images ---
            images_data = self._extract_images(response, url)
            images_without_alt = sum(1 for img in images_data if not img["has_alt"])
            extra_data["total_images"] = len(images_data)
            extra_data["images"] = images_data[:200]

            # --- Word count + body text ---
            body_text = " ".join(response.css("body *::text").getall())
            word_count = len(re.findall(r"\b\w+\b", body_text))
            extra_data["body_text"] = body_text[:5000] if body_text else ""

            # --- URL depth ---
            url_path = urlparse(url).path
            extra_data["url_depth"] = url_path.rstrip("/").count("/")

            # --- v0.5.0: Accessibility data extraction ---
            extra_data["a11y"] = self._extract_accessibility(response, url, images_data)

        extra_data["redirect_chain"] = redirect_chain
        extra_data["redirect_hops"] = len(redirect_chain) - 1 if len(redirect_chain) > 1 else 0

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
            "redirect_chain": redirect_chain,
            "depth": depth,
            "extra_data": extra_data,
        }
