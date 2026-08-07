import httpx
from dataclasses import dataclass

YELP_BASE = "https://api.yelp.com/v3"


@dataclass
class YelpClient:
    api_key: str

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def search_businesses(self, location: str, category: str, limit: int = 50) -> list[dict]:
        resp = httpx.get(
            f"{YELP_BASE}/businesses/search",
            headers=self._headers,
            params={"location": location, "categories": category, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        return [self._normalize_search(b) for b in resp.json().get("businesses", [])]

    def get_business(self, yelp_id: str) -> dict:
        resp = httpx.get(
            f"{YELP_BASE}/businesses/{yelp_id}",
            headers=self._headers,
            timeout=10,
        )
        resp.raise_for_status()
        return self._normalize_detail(resp.json())

    def _normalize_search(self, b: dict) -> dict:
        loc = b.get("location", {})
        return {
            "yelp_id": b.get("id"),
            "name": b.get("name"),
            "address": " ".join(filter(None, loc.get("display_address", []))),
            "city": loc.get("city"),
            "state": loc.get("state"),
            "phone": b.get("display_phone"),
            "website": None,
            "rating": b.get("rating"),
            "review_count": b.get("review_count"),
            "photos": b.get("photos", []),
        }

    def _normalize_detail(self, b: dict) -> dict:
        return {
            "yelp_id": b.get("id"),
            "name": b.get("name"),
            "photos": b.get("photos", []),
            "hours": b.get("hours", [{}])[0].get("open", []) if b.get("hours") else [],
            "price_range": b.get("price"),
            "categories": [c["title"] for c in b.get("categories", [])],
            "description": None,
        }
