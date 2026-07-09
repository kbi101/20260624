"""Wikipedia page fetcher via Morphos web_fetch tool. Adds per-request throttle for crawl compliance."""

import time

from morphos.tools.web_fetch import WebFetch

_REQUEST_DELAY = 3.0
_last_ts = [0.0]


def _throttle():
    elapsed = time.monotonic() - _last_ts[0]
    if elapsed < _REQUEST_DELAY:
        time.sleep(_REQUEST_DELAY - elapsed)
    _last_ts[0] = time.monotonic()


def fetch_full_page(url, timeout=15):
    """Fetch full Wikipedia article page using local Playwright browser. Returns all paragraph text."""
    _throttle()
    fetched = WebFetch(timeout=timeout).execute(url)
    
    # The tool returns up to 6000 chars by default — that's fine for now since we feed LLM chunks anyway.
    # If it gets truncated mid-sentence later phases we increase page limits.
    return fetched
