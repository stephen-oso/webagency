import pytest
import respx
import httpx
from app.services.google_places import GooglePlacesClient


@pytest.fixture
def client():
    return GooglePlacesClient(api_key="test-key")


@respx.mock
def test_search_businesses_returns_normalized_results(client):
    respx.get("https://maps.googleapis.com/maps/api/geocode/json").mock(
        return_value=httpx.Response(200, json={
            "results": [{"geometry": {"location": {"lat": 43.65, "lng": -79.38}}}]
        })
    )
    respx.get("https://maps.googleapis.com/maps/api/place/nearbysearch/json").mock(
        return_value=httpx.Response(200, json={
            "results": [
                {"place_id": "abc123", "name": "Mike's Plumbing", "vicinity": "123 Main St",
                 "rating": 4.2, "user_ratings_total": 38, "photos": [{"photo_reference": "ref1"}]}
            ],
            "status": "OK"
        })
    )
    results = client.search_businesses("Toronto, ON", "plumber")
    assert len(results) == 1
    assert results[0]["place_id"] == "abc123"
    assert results[0]["photos"] == ["ref1"]


@respx.mock
def test_get_place_details_extracts_city_state(client):
    respx.get("https://maps.googleapis.com/maps/api/place/details/json").mock(
        return_value=httpx.Response(200, json={
            "result": {
                "place_id": "abc123",
                "name": "Mike's Plumbing",
                "formatted_address": "123 Main St, Toronto, ON M4B 1B3, Canada",
                "address_components": [
                    {"types": ["locality"], "long_name": "Toronto", "short_name": "Toronto"},
                    {"types": ["administrative_area_level_1"], "long_name": "Ontario", "short_name": "ON"},
                ],
                "formatted_phone_number": "416-555-0123",
                "website": None,
                "rating": 4.2,
                "user_ratings_total": 38,
                "photos": [],
            }
        })
    )
    details = client.get_place_details("abc123")
    assert details["city"] == "Toronto"
    assert details["state"] == "ON"
    assert details["phone"] == "416-555-0123"
    assert details["website"] is None


def test_get_photo_url_builds_correct_url(client):
    url = client.get_photo_url("photoref123")
    assert "photo_reference=photoref123" in url
    assert "maxwidth=1200" in url
    assert "key=test-key" in url


def test_get_photo_url_custom_max_width(client):
    url = client.get_photo_url("photoref456", max_width=800)
    assert "maxwidth=800" in url
