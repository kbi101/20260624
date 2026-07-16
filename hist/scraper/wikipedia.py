"""Wikipedia page fetcher via Morphos WebFetch tool with page cache."""

import time
from morphos.tools.web_fetch import WebFetch
from hist.cache.page_cache import PageCache

_REQUEST_DELAY = 3.0
_last_ts = [0.0]
_page_cache = PageCache()


def _throttle():
    elapsed = time.monotonic() - _last_ts[0]
    if elapsed < _REQUEST_DELAY:
        time.sleep(_REQUEST_DELAY - elapsed)
    _last_ts[0] = time.monotonic()


def fetch_full_page(url, timeout=15):
    """Fetch full Wikipedia article page. Returns cleaned text (uses cache when fresh)."""
    cached = _page_cache.get(url)
    if cached is not None:
        return cached[:12000]

    _throttle()
    fetched = WebFetch(timeout=timeout).execute(url)
    _page_cache.put(url, fetched)
    return fetched[:12000]
