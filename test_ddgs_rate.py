import time
from duckduckgo_search import DDGS

for i in range(6):
    time.sleep(0.5)
    ddgs = DDGS()
    results = list(ddgs.text("SPY ETF price", max_results=3))
    print(f"Call {i}: {len(results)} results")
