"""Tier 2 — Extraction cache (entities + relations) with no expiration."""

import os
import json
import re
import time

CACHE_DIR = "data/hist_cache/extraction_cache"


def _slug_from_url(url):
    slug = url.rsplit("/", 1)[-1].lower().replace("_", "-")
    return re.sub(r"[^a-z0-9\-\.]", "", slug)


class ExtractionCache:
    def _path(self, url):
        return os.path.join(CACHE_DIR, f"{_slug_from_url(url)}.json")

    def get(self, url):
        p = self._path(url)
        if not os.path.exists(p):
            return None
        try:
            with open(p, "r") as f:
                data = json.load(f)
            return {"entities": data["entities"], "relations": data["relations"]}
        except (json.JSONDecodeError, KeyError):
            return None

    def put(self, url, entities, relations):
        os.makedirs(CACHE_DIR, exist_ok=True)
        data = {
            "url": url,
            "extracted_at": time.time(),
            "entities": entities,
            "relations": relations
        }
        with open(self._path(url), "w") as f:
            json.dump(data, f, indent=2)
