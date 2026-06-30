"""Financial data tool using yfinance — no scraping, no captcha."""

import warnings
from morphos.tools.registry import Tool


class Finance(Tool):
    @property
    def name(self) -> str:
        return "finance"

    @property
    def description(self) -> str:
        return (
            "Look up current stock or ETF price, previous close, market cap, and basic info. "
            "Pass either a ticker symbol (e.g. 'AAPL', 'SPY') or a query like "
            "'current price of SPY ETF'."
        )

    def execute(self, symbol: str = "", text_query: str = "") -> str:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import yfinance as yf

        # If given a free-text query instead of a ticker, extract the likely symbol
        sym = symbol.strip().upper() if symbol else ""
        if not sym and text_query:
            sym = _extract_ticker(text_query)

        if not sym:
            return "Could not determine a valid stock/ETF symbol from your input."

        try:
            t = yf.Ticker(sym)
            info = t.fast_info

            lines = []
            name = info.get("companyName", sym) or info.get("symbol", sym)
            lines.append(f"Symbol: {sym} | {name}")

            # Price data
            price = getattr(info, "lastPrice", None)
            prev_close = getattr(info, "lastDayClose", None)
            market_cap = getattr(info, "marketCap", None)

            if price is not None:
                lines.append(f"Latest Price: ${price:.2f}")
            if prev_close is not None:
                change = price - prev_close if price else 0
                pct = (change / prev_close * 100) if prev_close else 0
                lines.append(f"Previous Close: ${prev_close:.2f} ({change:+.2f} {pct:+.2f}%)")
            if market_cap is not None and market_cap > 0:
                if market_cap > 1e12:
                    lines.append(f"Market Cap: ${market_cap/1e12:.2f}T")
                elif market_cap > 1e9:
                    lines.append(f"Market Cap: ${market_cap/1e9:.2f}B")

            # Try to get today's summary range if available
            try:
                hist = t.history(period="1d")
                if not hist.empty:
                    row = hist.iloc[-1]
                    lines.append(f"Today's Range: ${row['Low']:.2f} – ${row['High']:.2f}")
                    lines.append(f"Volume: {int(row['Volume']):,}")
            except Exception:
                pass

            return "\n".join(lines) if len(lines) > 1 else ("No data available for symbol " + sym)

        except Exception as e:
            return f"Finance lookup failed for '{sym}': {e}"


def _extract_ticker(text: str) -> str:
    """Best-effort ticker extraction from a natural language query."""
    import re

    STOP = {
        "THE", "FOR", "AND", "WITH", "FROM", "ABOUT", "TO", "OF", "IN",
        "IS", "IT", "ON", "AS", "AT", "BY", "UP", "AN", "BE", "A",
        "PRICE", "PRICES", "STOCK", "QUOTE", "QUOTES", "DATA", "NEWS",
        "INFO", "TODAY", "CURRENT", "REALTIME", "MARKET", "TREND",
        "REPORT", "BASIC", "LOOK", "UP", "GET", "GETS", "GIVE",
        "WHAT", "HOW", "WHERE", "WHEN", "WHO", "WHY", "CAN", "WILL",
        "HAVE", "HAS", "HAD", "DOES", "DID", "COULD", "SHOULD",
        "ETF", "FUND", "INDEX", "TICKER", "SYMBOL", "STOCKS",
        "ME", "MY", "YOUR", "MANY", "NAV", "VALUE", "USE",
    }

    candidates = re.findall(r"\b[A-Z]{1,5}\b", text.upper())
    for c in candidates:
        if c not in STOP:
            return c
    return ""
