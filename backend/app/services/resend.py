"""Resend email delivery service."""

import httpx
from dataclasses import dataclass

RESEND_BASE = "https://api.resend.com"

EMAIL_TEMPLATE = """<html><body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<p>Hi {business_name} team,</p>
<p>I built you a website — take a look:</p>
<p><a href="{site_url}" style="font-size: 18px; color: #0066cc;">{site_url}</a></p>
<p>I noticed {business_name} in {city} didn't have a website (or the current one was outdated), so I put this together based on your {source} listing. It's live now.</p>
<p>If you'd like to keep it — and get your own domain, edits, and SEO — reply to this email and we'll sort out the details.</p>
<p>If it's not for you, no worries. Just ignore this.</p>
<p>— The Web Agency</p>
</body></html>"""


@dataclass
class ResendClient:
    api_key: str
    from_email: str = "hello@youragency.com"

    def send_email(
        self,
        to: str,
        subject: str,
        business_name: str,
        city: str,
        site_url: str,
        source: str = "Google",
    ) -> dict:
        """Send an outreach email via Resend API.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            business_name: Name of the business.
            city: City the business is in.
            site_url: URL of the built site.
            source: Source listing (e.g., "Google", "Yelp").

        Returns:
            Dict with keys ``id`` (str) and ``status`` ("sent").
        """
        html = EMAIL_TEMPLATE.format(
            business_name=business_name,
            city=city,
            site_url=site_url,
            source=source,
        )
        resp = httpx.post(
            f"{RESEND_BASE}/emails",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": self.from_email,
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return {"id": resp.json().get("id"), "status": "sent"}
