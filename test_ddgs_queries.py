from duckduckgo_search import DDGS

queries = [
    "current price of SPY ETF",
    "SPY ETF current price Yahoo Finance",
    "current stock price of SPY",
    "SPY ticker symbol live price",
    "SPY ETF current price ticker",
    "SPY ETF stock price today",
]

for q in queries:
    results = list(DDGS().text(q, max_results=3))
    print(f"\"{q}\" => {len(results)} results")
