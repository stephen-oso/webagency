import httpx
from dataclasses import dataclass


PLACES_BASE = "https://maps.googleapis.com/maps/api/place"
GEOCODE_BASE = "https://maps.googleapis.com/maps/api/geocode"


@dataclass
class GooglePlacesClient:
    api_key: str

    def search_businesses(self, region: str, category: str, radius_m: int = 50000) -> list[dict]:
        """Search for businesses using Google Places nearby search API.

        **IMPORTANT:** The Google nearbysearch API does not return city and state information.
        This method returns empty strings for 'city' and 'state' fields. To populate these fields,
        you must call get_place_details() with the place_id for each result.

        Args:
            region: The region/address to search around
            category: The business category/keyword to search for
            radius_m: Search radius in meters (default: 50000)

        Returns:
            A list of normalized business result dicts with empty city/state fields.
        """
        coords = self._geocode(region)
        params = {
            "location": f"{coords['lat']},{coords['lng']}",
            "radius": radius_m,
            "keyword": category,
            "key": self.api_key,
        }
        results = []
        url = f"{PLACES_BASE}/nearbysearch/json"
        while url:
            resp = httpx.get(url if url.startswith("http") else f"{PLACES_BASE}/nearbysearch/json", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for place in data.get("results", []):
                results.append(self._normalize_search_result(place))
            next_token = data.get("next_page_token")
            url = f"{PLACES_BASE}/nearbysearch/json?pagetoken={next_token}&key={self.api_key}" if next_token else None
            params = {}
        return results

    def get_place_details(self, place_id: str) -> dict:
        fields = "place_id,name,formatted_address,address_components,formatted_phone_number,website,opening_hours,editorial_summary,photos,rating,user_ratings_total"
        resp = httpx.get(
            f"{PLACES_BASE}/details/json",
            params={"place_id": place_id, "fields": fields, "key": self.api_key},
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        return self._normalize_details(result)

    def get_photo_url(self, photo_reference: str, max_width: int = 1200) -> str:
        return (
            f"{PLACES_BASE}/photo"
            f"?maxwidth={max_width}&photo_reference={photo_reference}&key={self.api_key}"
        )

    def _geocode(self, region: str) -> dict:
        resp = httpx.get(
            f"{GEOCODE_BASE}/json",
            params={"address": region, "key": self.api_key},
            timeout=10,
        )
        resp.raise_for_status()
        location = resp.json()["results"][0]["geometry"]["location"]
        return {"lat": location["lat"], "lng": location["lng"]}

    def _normalize_search_result(self, place: dict) -> dict:
        return {
            "place_id": place.get("place_id"),
            "name": place.get("name"),
            "address": place.get("vicinity"),
            # Google's nearbysearch API does not return city/state data. These must be populated
            # by calling get_place_details() and using _normalize_details() instead.
            "city": "",
            "state": "",
            "phone": None,
            "website": None,
            "rating": place.get("rating"),
            "review_count": place.get("user_ratings_total"),
            "photos": [p["photo_reference"] for p in place.get("photos", [])],
        }

    def _normalize_details(self, result: dict) -> dict:
        city, state = "", ""
        for comp in result.get("address_components", []):
            if "locality" in comp["types"]:
                city = comp["long_name"]
            if "administrative_area_level_1" in comp["types"]:
                state = comp["short_name"]
        return {
            "place_id": result.get("place_id"),
            "name": result.get("name"),
            "address": result.get("formatted_address"),
            "city": city,
            "state": state,
            "phone": result.get("formatted_phone_number"),
            "website": result.get("website"),
            "hours": result.get("opening_hours", {}).get("weekday_text", []),
            "description": result.get("editorial_summary", {}).get("overview"),
            "photos": [p["photo_reference"] for p in result.get("photos", [])],
            "rating": result.get("rating"),
            "review_count": result.get("user_ratings_total"),
        }
