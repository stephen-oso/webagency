from playwright.sync_api import sync_playwright, Error as PlaywrightError


def score_website(url: str) -> int:
    """Score a website 0-10. 0 = no site/404. <=4 = outreach candidate."""
    if not url:
        return 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                resp = page.goto(url, timeout=8000, wait_until="domcontentloaded")
                if resp is None or resp.status >= 400:
                    return 0
                content = page.content()
                score = 5
                if len(content) < 2000:
                    score -= 3
                if "coming soon" in content.lower() or "under construction" in content.lower():
                    score -= 4
                if not page.query_selector("meta[name='viewport']"):
                    score -= 2
                if page.query_selector("table[width]") or page.query_selector("font[face]"):
                    score -= 2
                return max(0, min(10, score))
            finally:
                browser.close()
    except (PlaywrightError, Exception):
        return 0
