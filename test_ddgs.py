import asyncio
from duckduckgo_search import DDGS


async def ddg():
    results = list(DDGS().text("SPY ETF price today", max_results=5))
    for r in results:
        print(f"• {r.get('title', '')}")
        print(f"  URL: {r.get('href', '')}")
        print(f"  Body: {r.get('body', '')[:200]}")


asyncio.run(ddg())
