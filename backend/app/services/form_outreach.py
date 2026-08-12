"""Contact form outreach service using Playwright."""

import logging
from dataclasses import dataclass

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# Rotate through a few realistic user-agent strings to avoid bot detection.
USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.4 Safari/605.1.15"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
]

FORM_MESSAGE = (
    "Hi, I built {business_name} a website — {site_url}\n\n"
    "I noticed you didn't have a website (or the current one was outdated), "
    "so I put one together using your online listings. It's live now.\n\n"
    "If you'd like to keep it and get your own domain + edits, just reply here. "
    "If not, no worries.\n\n"
    "— The Web Agency"
)

_USER_AGENT_INDEX = 0


def _next_user_agent() -> str:
    global _USER_AGENT_INDEX
    agent = USER_AGENTS[_USER_AGENT_INDEX % len(USER_AGENTS)]
    _USER_AGENT_INDEX += 1
    return agent


@dataclass
class FormOutreachClient:
    def submit_form(self, website_url: str, business_name: str, site_url: str) -> bool:
        """Attempt to find and fill a contact form on the business's existing website.

        Args:
            website_url: The business's existing website URL.
            business_name: Name of the business (used in the message body).
            site_url: URL of the newly built site (included in the message).

        Returns:
            True if a form was found and submitted, False otherwise.
        """
        message = FORM_MESSAGE.format(business_name=business_name, site_url=site_url)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    context = browser.new_context(user_agent=_next_user_agent())
                    page = context.new_page()
                    try:
                        page.goto(
                            website_url,
                            timeout=10000,
                            wait_until="domcontentloaded",
                        )

                        # Try to navigate to a contact page if one exists.
                        contact_link = page.query_selector(
                            "a[href*='contact'], a:text-matches('contact', 'i')"
                        )
                        if contact_link:
                            contact_link.click()
                            page.wait_for_load_state(
                                "domcontentloaded", timeout=5000
                            )

                        textarea = page.query_selector("textarea")
                        if not textarea:
                            logger.info(
                                f"No textarea found on {website_url} — skipping form outreach"
                            )
                            return False

                        name_field = page.query_selector(
                            "input[name*='name'], input[placeholder*='name' i]"
                        )
                        email_field = page.query_selector(
                            "input[type='email'], input[name*='email']"
                        )

                        if name_field:
                            name_field.fill("Web Agency")
                        if email_field:
                            email_field.fill("hello@youragency.com")

                        textarea.fill(message)

                        submit = page.query_selector(
                            "button[type='submit'], input[type='submit']"
                        )
                        if submit:
                            submit.click()
                            page.wait_for_timeout(2000)
                            logger.info(f"Form submitted successfully for {website_url}")
                            return True

                        logger.info(
                            f"No submit button found on {website_url} — skipping form outreach"
                        )
                        return False
                    finally:
                        context.close()
                finally:
                    browser.close()
        except (PlaywrightTimeout, Exception) as e:
            logger.warning(f"Form outreach failed for {website_url}: {e}")
            return False
