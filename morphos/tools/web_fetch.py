"""Web fetch tool using Playwright headless Chrome for full page rendering."""

import re
from dataclasses import dataclass

from morphos.tools.browser import get_page
from readability.readability import Document
from bs4 import BeautifulSoup

from morphos.tools.registry import Tool


@dataclass
class WebFetch(Tool):
    timeout: int = 30

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return (
            "Fetch a webpage using a headless browser and extract readable text. "
            "Provide a full URL including https://"
        )

    def execute(self, url: str) -> str:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        page = get_page(self.timeout)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
            # Give JS a moment to render dynamic content
            page.wait_for_timeout(2000)
            title = page.title() or ""
            body_html = page.inner_html("body")

            doc = Document(body_html)
            content_html = doc.summary() or body_html
            final_title = doc.title() or title or "Page"

            text = BeautifulSoup(content_html, "html.parser").get_text(
                separator="\n", strip=True
            )
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))

            return f"[{final_title}]\n{cleaned[:6000]}"

        except Exception as e:
            # Grab whatever rendered so far before the error
            try:
                title = page.title() or "Page"
                text = page.inner_text("body") or ""
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                return f"[{title}]\n" + "\n".join(lines)[:6000]
            except Exception:
                return f"Fetch failed: {e}"
        finally:
            page.close()
