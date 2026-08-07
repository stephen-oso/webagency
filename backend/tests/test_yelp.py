import pytest
import respx
import httpx
from app.services.yelp import YelpClient


@pytest.fixture
def client():
    return YelpClient(api_key="test-yelp-key")


@respx.mock
def test_search_returns_normalized_results(client):
    respx.get("https://api.yelp.com/v3/businesses/search").mock(
        return_value=httpx.Response(200, json={
            "businesses": [{
                "id": "yelp-abc", "name": "City Salon",
                "location": {"city": "Vancouver", "state": "BC", "display_address": ["123 Robson St", "Vancouver, BC"]},
                "display_phone": "604-555-0199", "rating": 4.7, "review_count": 120, "photos": []
            }]
        })
    )
    results = client.search_businesses("Vancouver, BC", "salon")
    assert results[0]["yelp_id"] == "yelp-abc"
    assert results[0]["city"] == "Vancouver"


@respx.mock
def test_get_business_returns_detail(client):
    respx.get("https://api.yelp.com/v3/businesses/yelp-abc").mock(
        return_value=httpx.Response(200, json={
            "id": "yelp-abc", "name": "City Salon",
            "photos": ["https://yelp.com/photo1.jpg"],
            "price": "$$", "categories": [{"title": "Hair Salons"}], "hours": []
        })
    )
    detail = client.get_business("yelp-abc")
    assert detail["price_range"] == "$$"
    assert "Hair Salons" in detail["categories"]


@respx.mock
def test_search_includes_all_required_keys(client):
    respx.get("https://api.yelp.com/v3/businesses/search").mock(
        return_value=httpx.Response(200, json={
            "businesses": [{
                "id": "yelp-xyz", "name": "Test Biz",
                "location": {"city": "Calgary", "state": "AB", "display_address": ["456 Centre St"]},
                "display_phone": "403-555-0100", "rating": 3.5, "review_count": 20, "photos": ["url1"]
            }]
        })
    )
    results = client.search_businesses("Calgary, AB", "restaurant")
    assert len(results) == 1
    r = results[0]
    for key in ("yelp_id", "name", "address", "city", "state", "phone", "website", "rating", "review_count", "photos"):
        assert key in r, f"Missing key: {key}"
    assert r["address"] == "456 Centre St"
    assert r["photos"] == ["url1"]


@respx.mock
def test_get_business_includes_all_required_keys(client):
    respx.get("https://api.yelp.com/v3/businesses/yelp-xyz").mock(
        return_value=httpx.Response(200, json={
            "id": "yelp-xyz", "name": "Test Biz",
            "photos": [], "price": "$", "categories": [{"title": "Restaurants"}],
            "hours": [{"open": [{"day": 0, "start": "0900", "end": "1700"}]}]
        })
    )
    detail = client.get_business("yelp-xyz")
    for key in ("yelp_id", "name", "photos", "hours", "price_range", "categories", "description"):
        assert key in detail, f"Missing key: {key}"
    assert detail["hours"] == [{"day": 0, "start": "0900", "end": "1700"}]
