import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def score_metric(value: Optional[float], good: float, poor: float) -> str:
    if value is None:
        return "unknown"
    if value <= good:
        return "good"
    if value <= poor:
        return "needs_improvement"
    return "poor"


def score_cwv(metrics: dict) -> dict:
    lcp = metrics.get("lcp")
    cls_val = metrics.get("cls")
    fcp = metrics.get("fcp")
    ttfb = metrics.get("ttfb")
    scores = {
        "lcp_score": score_metric(lcp, 2500, 4000),
        "cls_score": score_metric(cls_val, 0.1, 0.25),
        "fcp_score": score_metric(fcp, 1800, 3000),
        "ttfb_score": score_metric(ttfb, 800, 1800),
    }
    poor_count = sum(1 for v in scores.values() if v == "poor")
    good_count = sum(1 for v in scores.values() if v == "good")
    if poor_count >= 2:
        scores["overall"] = "poor"
    elif good_count >= 3:
        scores["overall"] = "good"
    else:
        scores["overall"] = "needs_improvement"
    return scores


async def measure_cwv(url: str, timeout: int = 30) -> dict:
    try:
        from playwright.async_api import async_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.warning("playwright not installed — CWV measurement unavailable")
        return {}

    metrics = {}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (compatible; WebCrawlerPro/1.0)",
            )
            page = await context.new_page()

            resource_count = 0
            resource_size = 0

            def on_response(response):
                nonlocal resource_count, resource_size
                resource_count += 1
                headers = response.headers
                cl = headers.get("content-length")
                if cl and cl.isdigit():
                    resource_size += int(cl)

            page.on("response", on_response)

            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            except PWTimeout:
                logger.warning("CWV navigation timeout for %s", url)

            raw = await page.evaluate("""
            () => new Promise((resolve) => {
                const m = {};
                const nav = performance.getEntriesByType("navigation")[0];
                if (nav) {
                    m.ttfb = nav.responseStart - nav.requestStart;
                    m.tti  = nav.domInteractive   - nav.startTime;
                    m.tbt  = nav.domContentLoadedEventEnd - nav.domInteractive;
                }
                performance.getEntriesByType("paint").forEach(p => {
                    if (p.name === "first-contentful-paint") m.fcp = p.startTime;
                });
                let lcp_val = 0;
                let cls_val = 0;
                try {
                    new PerformanceObserver(list => {
                        const e = list.getEntries();
                        if (e.length) lcp_val = e[e.length - 1].startTime;
                    }).observe({type: "largest-contentful-paint", buffered: true});
                    new PerformanceObserver(list => {
                        list.getEntries().forEach(e => { if (!e.hadRecentInput) cls_val += e.value; });
                    }).observe({type: "layout-shift", buffered: true});
                } catch(err) {}
                m.dom_size = document.querySelectorAll("*").length;
                setTimeout(() => {
                    m.lcp = lcp_val;
                    m.cls = Math.round(cls_val * 1000) / 1000;
                    resolve(m);
                }, 3000);
            })
            """)

            await browser.close()

            metrics = {
                "lcp":            raw.get("lcp"),
                "cls":            raw.get("cls"),
                "fcp":            raw.get("fcp"),
                "ttfb":           raw.get("ttfb"),
                "tbt":            max(raw.get("tbt", 0), 0),
                "tti":            raw.get("tti"),
                "dom_size":       raw.get("dom_size"),
                "resource_count": resource_count,
                "resource_size_kb": round(resource_size / 1024, 1),
            }
            metrics["scores"] = score_cwv(metrics)

    except Exception as e:
        logger.error("CWV measurement failed for %s: %s", url, e)

    return metrics


def measure_cwv_sync(url: str, timeout: int = 30) -> dict:
    try:
        return asyncio.run(measure_cwv(url, timeout))
    except Exception as e:
        logger.error("measure_cwv_sync error: %s", e)
        return {}
