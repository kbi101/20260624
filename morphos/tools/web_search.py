"""Web search by typing into DuckDuckGo via Playwright + real Chrome.

Opens a new tab → types query into DDG → hits Enter → extracts results →
ranks them with learned heuristics so preferred sources surface first."""

import base64
import re
import time
import urllib.parse as urlparse

from morphos.tools.browser import get_page
from morphos.tools.registry import Tool


def _decode_ddg_redirect(href: str) -> str:
    """Resolve DDG redirect wrapper URLs to the actual target URL.

    DDG organic results link through /l/ with encoded redirect params.
    Paid ads go through /y.js? with ad provider tracking — those are filtered out caller-side."""

    if not href:
        return ""

    # Skip DDG's own internal pages and ad redirects
    if href.startswith(("/y.js", "/t/", "/d/", "/html")):
        return ""
    if "duckduckgo.com/y.js" in href or "ad_provider" in href:
        return ""

    # If it's already a clean external URL, use as-is
    if href.startswith("http://") or href.startswith("https://"):
        return href

    # DDG organic redirect format: /l/?uddn=...&udd=https://target-url...
    if href.startswith("/l/"):
        parsed = urlparse.urlparse(href.replace("//", "/"))
        params = urlparse.parse_qs(parsed.query)
        # Try udd (often base64) then uddn (fallback plain URL)
        for key in ("udd", "uddn"):
            val = params.get(key, [None])[0]
            if not val:
                continue
            # Already decoded URL
            if val.startswith("http"):
                return val
            # base64-encoded — fix padding before decoding
            try:
                padded = val + "=" * (-len(val) % 4)
                decoded = base64.b64decode(padded).decode("utf-8")
                if decoded.startswith("http"):
                    return decoded
            except Exception:
                pass
        return ""

    # Last resort: extract any http URL from the href string
    m = re.search(r"https?://[^\s&\"']+|www\.[^\s&\"']+", href)
    if m:
        url = m.group(0)
        if not url.startswith("http"):
            url = "https://" + url
        return url

    return ""


def _is_ad_article(article_html: str, article_inner: str) -> bool:
    """Detect and filter out sponsored/ad articles from DDG results."""
    ad_signals = ["sponsored", "promoted", "ad-", ".ddg_sp"]
    if any(s.lower() in article_inner.lower() for s in ad_signals):
        return True
    if "class=\"\"" in article_html or "data-testid=\"paid" in article_html:
        return True
    return False


class WebSearch(Tool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search DuckDuckGo using a real Chrome browser and return result titles, "
            "snippets, and URLs. Use this when looking up current information."
        )

    def execute(self, query: str, max_results: int = 8) -> str:
        page = get_page(30)
        try:
            page.goto("https://duckduckgo.com/", wait_until="domcontentloaded")

            with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                page.fill('input[name="q"]', query)
                page.keyboard.press("Enter")

            time.sleep(2)

            results = []

            articles = page.query_selector_all(".results--main article")[:max_results * 3]
            for article in articles:
                # Skip ad/sponsored content
                art_html = article.get_attribute("class") or ""
                try:
                    art_inner = (article.inner_text() or "").lower()
                except Exception:
                    art_inner = ""
                if _is_ad_article(art_html, art_inner):
                    continue

                title_el = article.query_selector("h2 a")
                link_el = article.query_selector("a[href]")

                title = title_el.inner_text() if title_el else ""
                raw_href = (link_el or title_el).get_attribute("href") if (link_el or title_el) else ""

                # Resolve DDG redirect URL to actual target
                href = _decode_ddg_redirect(raw_href)

                snippet = ""
                for sel in ["span:not([class])", "p", ".snippet"]:
                    s = article.query_selector(sel)
                    raw = s.inner_text() if s else ""
                    if len(raw.strip()) > 20:
                        snippet = raw.strip()[:400]
                        break

                if not snippet and title:
                    all_txt = (article.inner_text() or "").replace(title, "").strip()
                    lines = [l for l in all_txt.split("\n") if len(l.strip()) > 20]
                    if lines:
                        snippet = lines[0][:400]

                if title and href:
                    results.append((title, href, snippet))

            now_card = page.query_selector("[data-no-defer]")
            if not results and now_card:
                extra_text = now_card.inner_text()[:600]
                return f"Instant result:\n{extra_text}"

            if not results:
                for a in page.query_selector_all('a[href^="http"]')[:max_results * 3]:
                    href = a.get_attribute("href") or ""
                    text_clean = (a.inner_text() or "").strip()
                    if "duckduckgo.com" not in href and len(text_clean) > 25:
                        results.append((text_clean[:150], href, ""))

            # Re-rank results using learned heuristics
            results = self._rerank(query, results)

            return self._format(query, results)

        except Exception as e:
            return f"Search failed: {e}"
        finally:
            page.close()

    def _rerank(self, query: str, results: list) -> list:
        """Boost results that match learned heuristic sources to the top."""
        try:
            from morphos.heuristics import HeuristicEngine
            engine = HeuristicEngine()
            matched = engine.match(query)
            if not matched:
                return results

            preferred_domains = []
            for h in matched:
                ps = h.get("preferred_source", "")
                # Extract domain from preferred source
                try:
                    from urllib.parse import urlparse
                    d = urlparse(ps).netloc or ""
                    preferred_domains.append(d)
                except Exception:
                    pass

            if not preferred_domains:
                return results

            def score(r):
                href = r[1]
                for dom in preferred_domains:
                    if dom and re.search(re.escape(dom), href, re.IGNORECASE):
                        return 0  # highest priority
                return 1

            boosted = [r for r in results if score(r) == 0]
            rest = [r for r in results if score(r) == 1]
            return boosted + rest

        except Exception:
            return results

    @staticmethod
    def _format(query: str, results: list[tuple[str, str, str]]) -> str:
        if not results:
            return (
                f"No search results for \"{query}\". "
                "Try fetching a specific URL with web_fetch."
            )

        lines = []
        for title, link, snippet in results[:8]:
            line = f"• {title}\n  URL: {link}"
            if snippet:
                line += f"\n  {snippet[:300]}"
            lines.append(line)

        return f"Search results for \"{query}\":\n\n" + "\n".join(lines)
