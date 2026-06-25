from playwright.sync_api import sync_playwright

with sync_playwright() as pwt:
    br = pwt.chromium.launch(headless=True)
    
    # Test DuckDuckGo HTML search via Playwright
    page = br.new_page()
    page.goto("https://html.duckduckgo.com/html/?q=weather+st+louis", wait_until="domcontentloaded")
    
    text = page.inner_text("body")[:500]
    print(f"DDG HTML body len: {len(text)}")
    print(f"Text preview: {text[:300]}")
    
    # Check result selectors
    for sel in [".result", ".result__title", "#links .result"]:
        count = len(page.query_selector_all(sel))
        print(f"{sel}: {count}")
    
    page.close()
