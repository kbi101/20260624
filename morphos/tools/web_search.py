"""Web search by typing into DuckDuckGo via Playwright + real Chrome.

Opens a new tab → types query into DDG → hits Enter → extracts results.
Works because DuckDuckGo doesn't block regular Chrome instances."""

import re
import time

from morphos.tools.browser import get_page
from morphos.tools.registry import Tool


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
            # Navigate to DuckDuckGo main site (not html endpoint)
            page.goto("https://duckduckgo.com/", wait_until="domcontentloaded")

            # Fill search box and submit
            with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                page.fill('input[name="q"]', query)
                page.keyboard.press("Enter")

            time.sleep(1)  # let results paint

            results = []

            # Main results live under .results--main > article > h2 > a
            articles = page.query_selector_all(".results--main article")[:max_results]
            for article in articles:
                title_el = article.query_selector("h2 a")
                link_el = article.query_selector("a[href]")

                title = title_el.inner_text() if title_el else ""
                href = (link_el or title_el).get_attribute("href") if (link_el or title_el) else ""

                # Snippet: find any span/text under the result
                snippet = ""
                for sel in ["span:not([class])", "p", ".snippet"]:
                    s = article.query_selector(sel)
                    raw = s.inner_text() if s else ""
                    if len(raw.strip()) > 20:
                        snippet = raw.strip()[:400]
                        break

                # Fallback: grab remaining text from the article, minus title/header nav
                if not snippet and title:
                    all_txt = (article.inner_text() or "").replace(title, "").strip()
                    lines = [l for l in all_txt.split("\n") if len(l.strip()) > 20]
                    if lines:
                        snippet = lines[0][:400]

                if title and href:
                    results.append((title, href, snippet))

            # Also grab the "now card" / instant answer content (weather, stocks etc)
            now_card = page.query_selector("[data-no-defer]")
            if not results and now_card:
                extra_text = now_card.inner_text()[:600]
                return f"Instant result:\n{extra_text}"

            # Fallback: scrape all external links off the body
            if not results:
                for a in page.query_selector_all('a[href^="http"]')[:max_results * 3]:
                    href = a.get_attribute("href") or ""
                    text_clean = (a.inner_text() or "").strip()
                    if "duckduckgo.com" not in href and len(text_clean) > 25:
                        results.append((text_clean[:150], href, ""))

            return self._format(query, results)

        except Exception as e:
            return f"Search failed: {e}"
        finally:
            page.close()

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
