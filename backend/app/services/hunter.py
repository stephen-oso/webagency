"""Hunter.io email lookup service."""

import httpx
from dataclasses import dataclass

HUNTER_BASE = "https://api.hunter.io/v2"


@dataclass
class HunterClient:
    api_key: str

    def find_email(self, domain: str, company: str) -> str | None:
        """Look up a business email via Hunter.io domain-search.

        Args:
            domain: The business's domain (e.g. "mikesplumbing.com").
            company: The business name (used as a hint for Hunter).

        Returns:
            The first found email address, or None if not found or on error.
        """
        if not self.api_key:
            return None
        try:
            resp = httpx.get(
                f"{HUNTER_BASE}/domain-search",
                params={
                    "domain": domain,
                    "company": company,
                    "api_key": self.api_key,
                    "limit": 1,
                },
                timeout=10,
            )
            resp.raise_for_status()
            emails = resp.json().get("data", {}).get("emails", [])
            return emails[0]["value"] if emails else None
        except Exception:
            return None
