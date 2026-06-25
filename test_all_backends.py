import subprocess
import sys

# Test 1: DDGS
print("=== Test DDGS ===")
try:
    import warnings; warnings.filterwarnings("ignore")
    from duckduckgo_search import DDGS
    results = list(DDGS().text("weather St Louis", max_results=3))
    print(f"Results: {len(results)}")
    for r in results[:2]:
        print(f"  {r.get('title','')} => {r.get('href','')}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Playwright Google
print("\n=== Test Playwright Google ===")
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pwt:
        br = pwt.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://www.google.com/search?q=weather+st+louis", wait_until="domcontentloaded")
        text = page.inner_text("body")[:300]
        # Check if it's a captcha page
        has_captcha = any(kw in text.lower() for kw in ["verify", "captcha", "sorry", "blocked"])
        articles = len(page.query_selector_all("article"))
        print(f"Body len: {len(text)}, Captcha: {has_captcha}, Articles: {articles}")
        br.close()
except Exception as e:
    print(f"Error: {e}")

# Test 3: Direct weather.gov fetch
print("\n=== Test web_fetch weather.gov ===")
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pwt:
        br = pwt.chromium.launch(headless=True)
        page = br.new_page()
        page.goto("https://forecast.weather.gov/MapClick.php?CityName=St+Louis&state=MO", wait_until="domcontentloaded")
        text = page.inner_text("body")[:500]
        print(f"Text: {text[:300]}")
        br.close()
except Exception as e:
    print(f"Error: {e}")
