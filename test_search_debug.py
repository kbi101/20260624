from playwright.sync_api import sync_playwright
import urllib.parse as parse

with sync_playwright() as pwt:
    browser = pwt.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(15000)

    for search_url in [
        "https://html.duckduckgo.com/html/?q=SPY+ETF+price",
        f"https://www.google.com/search?q=SPY+ETF+price&hl=en",
    ]:
        print(f"\n=== {search_url[:60]} ...")
        page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        title = page.title()
        body_len = len(page.inner_text("body"))
        print(f"Title: {title}, Body chars: {body_len}")

        # Check for captcha / verify prompts
        text = page.inner_text("body")[:400]
        for flag in ["Verify", "captcha", "Cloudflare", "too many requests"]:
            if flag.lower() in text.lower():
                print(f"FLAG: {flag} detected!")

        # Try selectors
        for sel in [".result", ".g", "#search a[href]", ".rc"]:
            count = len(page.query_selector_all(sel))
            if count:
                print(f"  {sel}: {count}")

    browser.close()
