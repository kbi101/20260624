"""Tier 1 — Persistent page text cache with 24-hour TTL."""

import os
import json
import re
import time

CACHE_DIR = "data/hist_cache/page_cache"
TTL_SECONDS = 86400  # 24 hours


def _slug_from_url(url):
    slug = url.rsplit("/", 1)[-1].lower().replace("_", "-")
    return re.sub(r"[^a-z0-9\-\.]", "", slug)


class PageCache:
    def _path(self, url):
        return os.path.join(CACHE_DIR, f"{_slug_from_url(url)}.json")

    def get(self, url):
        p = self._path(url)
        if not os.path.exists(p):
            return None
        try:
            with open(p, "r") as f:
                data = json.load(f)
            age = time.time() - data["fetched_at"]
            if age >= TTL_SECONDS:
                return None
            return data["text"]
        except (json.JSONDecodeError, KeyError):
            return None

    def put(self, url, text):
        os.makedirs(CACHE_DIR, exist_ok=True)
        data = {
            "url": url,
            "fetched_at": time.time(),
            "text": text
        }
        with open(self._path(url), "w") as f:
            json.dump(data, f)
