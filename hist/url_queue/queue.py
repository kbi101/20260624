"""Hist URL Queue — discover and manage Wikipedia pages to scrape."""

import json
import os
from urllib.parse import quote

QUEUE_PATH = "data/hist_url_queue.json"


def _load():
    if os.path.exists(QUEUE_PATH):
        with open(QUEUE_PATH) as f:
            return json.load(f)
    return {"pending": [], "completed": []}


def _save(data):
    data["pending"] = list(set(data["pending"]))
    data["completed"] = list(set(data["completed"]))
    with open(QUEUE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def add_to_queue(urls):
    """Add URL(s) to pending queue (deduped against already completed)."""
    urls = urls if isinstance(urls, list) else [urls]
    data = _load()
    for u in urls:
        if u not in data["pending"] and u not in data["completed"]:
            data["pending"].append(u)
    _save(data)


def get_next_url():
    """Pop one URL from pending queue."""
    data = _load()
    url = data["pending"].pop(0) if data["pending"] else None
    _save(data)
    return url


def mark_completed(url):
    """Mark a URL as successfully scraped."""
    data = _load()
    if url in data["pending"]:
        data["pending"].remove(url)
    data["completed"].append(url)
    _save(data)


def pending_count():
    data = _load()
    return len(data["pending"])


def wikipedia_seed(topic):
    """Add the Wikipedia page for a topic to the queue."""
    url = f"https://en.wikipedia.org/wiki/{quote(topic.replace(' ', '_'))}"
    add_to_queue(url)
    return url
