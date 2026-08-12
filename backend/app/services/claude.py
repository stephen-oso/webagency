"""Claude AI copy generation service for local business websites."""

import json
import anthropic
from dataclasses import dataclass


CATEGORY_TO_TEMPLATE = {
    "restaurant": "restaurant", "cafe": "restaurant",
    "plumber": "plumber", "plumbing": "plumber",
    "salon": "salon", "hair": "salon", "beauty": "salon",
    "dentist": "dentist", "dental": "dentist",
    "landscaping": "landscaping", "lawn": "landscaping",
    "retail": "retail", "boutique": "retail",
    "trades": "trades", "contractor": "trades", "handyman": "trades",
    "professional": "professional",
    "auto": "auto", "mechanic": "auto",
    "cleaning": "cleaning",
    "gym": "gym", "fitness": "gym",
    "photography": "photography", "photographer": "photography",
    "realestate": "realestate", "realtor": "realestate",
    "childcare": "childcare", "daycare": "childcare",
    "petservices": "petservices", "vet": "petservices", "grooming": "petservices",
}

OUTREACH_EMAIL_PROMPT = """Write a short, direct outreach email for a web agency that just built a free website for a local business.

Business name: {business_name}
City: {city}
New website URL: {site_url}

Tone: direct, not salesy. One person talking to another. Not pushy. Conversational.
Goal: Let them know the site exists and invite them to keep it if they want.
Subject line: "I built {business_name} a website — take a look"

Return ONLY a JSON object with exactly these keys:
{{
  "subject": "I built {business_name} a website — take a look",
  "body_html": "<html>...</html> — the full HTML email body (no <head> or DOCTYPE needed)"
}}

The body should be short (4-6 short paragraphs). Include the site URL as a clickable link. Sign off as "The Web Agency"."""

COPY_PROMPT = """You are writing website copy for a local business. Use ONLY real details from the data provided.
Do NOT use generic filler phrases. Reference specific services, location, or details that make this business unique.

Business data:
Name: {name}
City: {city}, {state}
Category: {category}
Description: {description}
Services: {services}
Rating: {rating} ({review_count} reviews)
Hours: {hours}

Return ONLY a JSON object with these exact keys:
{{
  "headline": "short punchy headline (max 8 words, references the business or location)",
  "subheadline": "1 sentence that says what they do and where (max 20 words)",
  "about": "2-3 sentences about the business using real details (max 60 words)",
  "services": ["service 1", "service 2", "service 3", "service 4"],
  "cta_text": "call to action button text (max 5 words)",
  "meta_description": "SEO description (max 155 chars)"
}}"""


@dataclass
class ClaudeClient:
    api_key: str

    def select_template(self, category: str) -> str:
        """Map a business category string to a template slug.

        Returns one of the 15 valid template slugs, defaulting to 'professional'
        for unknown categories.
        """
        normalized = category.lower().strip()
        return CATEGORY_TO_TEMPLATE.get(normalized, "professional")

    def generate_site_copy(self, business_data: dict, assets: dict) -> dict:
        """Generate structured website copy for a local business using Claude.

        Args:
            business_data: Dict with keys: name, city, state, category.
            assets: Dict with keys: description, services, rating, review_count, hours.

        Returns:
            Dict with keys: headline, subheadline, about, services, cta_text, meta_description.
        """
        prompt = COPY_PROMPT.format(
            name=business_data.get("name", ""),
            city=business_data.get("city", ""),
            state=business_data.get("state", ""),
            category=business_data.get("category", ""),
            description=assets.get("description") or "Local business serving the community.",
            services=", ".join(assets.get("services") or []) or "General services",
            rating=assets.get("rating") or "N/A",
            review_count=assets.get("review_count") or 0,
            hours=str(assets.get("hours") or {}).replace("{", "").replace("}", ""),
        )

        client = anthropic.Anthropic(api_key=self.api_key)
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            raise RuntimeError(f"Claude API error: {exc}") from exc

        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as exc:
            raise ValueError(f"Claude returned invalid JSON: {exc}\nRaw response: {text[:500]}") from exc

    def generate_outreach_email(
        self, business_name: str, city: str, site_url: str
    ) -> dict:
        """Generate a personalised outreach email for a local business.

        Args:
            business_name: Name of the business.
            city: City the business operates in.
            site_url: URL of the newly built site.

        Returns:
            Dict with keys ``subject`` (str) and ``body_html`` (str).
        """
        prompt = OUTREACH_EMAIL_PROMPT.format(
            business_name=business_name,
            city=city,
            site_url=site_url,
        )

        client = anthropic.Anthropic(api_key=self.api_key)
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            raise RuntimeError(f"Claude API error: {exc}") from exc

        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Claude returned invalid JSON: {exc}\nRaw response: {text[:500]}"
            ) from exc
