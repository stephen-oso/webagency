"""Tests for HunterClient — mocked HTTP, no real Hunter calls."""

import os
import pytest
import respx
import httpx

# Ensure DATABASE_URL is set before app imports.
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webagency_test")

from app.services.hunter import HunterClient


@respx.mock
def test_find_email_returns_first_email():
    """find_email returns the first email value from Hunter's domain-search response."""
    respx.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "emails": [
                        {"value": "owner@mikesplumbing.com"},
                        {"value": "info@mikesplumbing.com"},
                    ]
                }
            },
        )
    )
    client = HunterClient(api_key="test-key")
    email = client.find_email("mikesplumbing.com", "Mike's Plumbing")
    assert email == "owner@mikesplumbing.com"


def test_find_email_returns_none_when_no_api_key():
    """find_email returns None immediately when api_key is empty."""
    client = HunterClient(api_key="")
    assert client.find_email("example.com", "Example") is None


@respx.mock
def test_find_email_returns_none_when_empty_email_list():
    """find_email returns None when Hunter returns an empty emails list."""
    respx.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(200, json={"data": {"emails": []}})
    )
    client = HunterClient(api_key="test-key")
    result = client.find_email("noemails.com", "No Emails Corp")
    assert result is None


@respx.mock
def test_find_email_returns_none_on_http_error():
    """find_email returns None (does not raise) on HTTP errors."""
    respx.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(403, json={"error": "forbidden"})
    )
    client = HunterClient(api_key="bad-key")
    result = client.find_email("example.com", "Example")
    assert result is None


def test_find_email_returns_none_on_network_exception():
    """find_email returns None when a network-level exception occurs."""
    client = HunterClient(api_key="test-key")
    with respx.mock:
        respx.get("https://api.hunter.io/v2/domain-search").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        result = client.find_email("offline.com", "Offline Corp")
    assert result is None
