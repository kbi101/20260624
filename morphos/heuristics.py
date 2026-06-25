"""Source heuristics — learned query-pattern → preferred-source mappings.

The heuristic engine scans incoming queries for known patterns and injects
source hints into the agent's system prompt so it picks working URLs first.
"""

import json
import os
import re


_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

HEURISTICS_PATH = os.path.join(_PROJECT_ROOT, "data", "search_heuristics.json")


def _load(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"heuristics": []}


class HeuristicEngine:
    """Match query patterns to preferred sources, inject hints into prompts."""

    def __init__(self, path=None):
        self.path = path or HEURISTICS_PATH
        self._data = _load(self.path)

    @property
    def heuristics(self):
        return self._data.get("heuristics", [])

    def match(self, query: str) -> list[dict]:
        """Return all heuristics matching the query."""
        matches = []
        for h in self.heuristics:
            pattern = h.get("pattern", "")
            if re.search(pattern, query, re.IGNORECASE):
                matches.append(h)
        return matches

    def extract_ticker(self, query: str) -> str | None:
        """Look for a stock ticker (1-5 uppercase letters) in the query."""
        m = re.search(r"\b([A-Z]{3,6})\b", query)
        return m.group(1) if m else None

    def resolve_url(self, template: str, query: str) -> str | None:
        """Expand a URL template by substituting ticker/exchange."""
        ticker = self.extract_ticker(query) or ""
        exchange = "NASDAQ"  # heuristic default
        url = template
        if url and "{ticker}" in url:
            url = url.replace("{ticker}", ticker)
        if url and "{exchange}" in url:
            url = url.replace("{exchange}", exchange)
        return url or None

    def build_prompt_hint(self, query: str) -> str | None:
        """Return a system-prompt snippet with preferred sources for this query."""
        matches = self.match(query)
        if not matches:
            return None

        resolved_urls = []
        general_hints = []

        for h in matches:
            source = h.get("preferred_source", "")
            resolved = self.resolve_url(source, query) or source
            notes = h.get("notes", "")
            has_ticker_var = "{ticker}" in resolved

            if not has_ticker_var or (has_ticker_var and bool(self.extract_ticker(query))):
                if not resolved_urls:
                    resolved_urls.append(
                        "KNOWN WORKING SOURCES — use web_fetch on these URLs directly instead of searching first:"
                    )
                resolved_urls.append(f"  - {resolved}")
                if notes:
                    resolved_urls.append(f"    Note: {notes}")
            else:
                general_hints.append(f"  - Source for this query type: {resolved}")

            fb = h.get("fallback_pattern")
            if fb:
                resolved_fb = self.resolve_url(fb, query) or fb
                resolved_urls.append(f"  - Fallback: {resolved_fb}")

        lines = []
        lines.extend(resolved_urls)
        lines.extend(general_hints)

        return "\n".join(lines) if lines else None

    def add_heuristic(self, pattern: str, preferred_source: str, notes: str = "",
                      ticker_hint: bool = False, fallback_pattern: str | None = None):
        """Add a new heuristic at runtime (called from reflector)."""
        self.heuristics.append({
            "pattern": pattern,
            "preferred_source": preferred_source,
            "fallback_pattern": fallback_pattern,
            "ticker_hint": ticker_hint,
            "notes": notes,
        })

    def save(self):
        """Persist heuristics back to disk."""
        data = _load(self.path) if os.path.exists(self.path) else {}
        data["heuristics"] = self.heuristics
        data.setdefault("description", "Query-pattern to preferred-source mappings.")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def find_ticker_in_text(self, text: str) -> str | None:
        """Try to extract a ticker from page content (e.g. 'PEP Stock Alerts')."""
        m = re.search(r"([A-Z]{3,6})\s*(stock|earnings|price)", text, re.IGNORECASE)
        if m:
            return m.group(1).upper()
        all_tickers = re.findall(r"\b(A[A-Z]{2})\b", text)
        if all_tickers:
            return all_tickers[0].upper()
        return None

    def learn_from_success(self, query: str, url_used: str):
        """Extract a heuristic from a successful (query, URL) pair."""
        domain = ""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url_used).netloc
        except Exception:
            domain = url_used

        # Check if we already have this domain in heuristics
        for h in self.heuristics:
            ps = h.get("preferred_source", "")
            if domain in ps or ps == domain:
                return  # heuristic exists

        query_lower = query.lower()
        pattern = ""
        ticker_hint = False
        ticker = self.extract_ticker(query)

        if any(kw in query_lower for kw in ("earnings", "er date", "earnings release")):
            pattern = "(earnings date|earnings release|earnings calendar)"
            ticker_hint = True
        elif any(kw in query_lower for kw in ("weather", "forecast", "temperature")):
            pattern = "(weather|forecast|temperature .* today)"
        elif any(kw in query_lower for kw in ("price", "cost", "trading")) and ticker:
            pattern = "(stock price|current price|what does .* cost)"
            ticker_hint = True
        else:
            return  # no recognizable pattern to learn

        self.add_heuristic(
            pattern=pattern,
            preferred_source=url_used,
            notes=f"Learned from successful session",
            ticker_hint=ticker_hint,
            fallback_pattern=None,
        )
        self.save()
