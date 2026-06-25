"""Shared Playwright browser lifecycle management."""

import atexit
from playwright.sync_api import sync_playwright, Browser, BrowserContext


class BrowserManager:
    _instance = None
    _pwt = None
    _browser: Browser | None = None
    _context: BrowserContext | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def ensure(self):
        if self._browser is None:
            self._pwt = sync_playwright().start()
            self._browser = self._pwt.chromium.launch(
                headless=False,
                channel="chrome",
            )
            self._context = self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 900},
            )

        return self._context

    @property
    def browser(self):
        self.ensure()
        return self._browser

    @property
    def context(self):
        self.ensure()
        return self._context

    def cleanup(self):
        if self._browser:
            self._browser.close()
        if self._pwt:
            self._pwt.stop()
        self._browser = None
        self._context = None


bm = BrowserManager()
atexit.register(bm.cleanup)


def get_page(timeout: int = 30):
    """Return a fresh page from the shared context."""
    page = bm.context.new_page()
    page.set_default_timeout(timeout * 1000)
    return page
