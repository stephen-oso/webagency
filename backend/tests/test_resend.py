"""Tests for ResendClient — mocked HTTP, no real Resend calls."""

import os
import pytest
import respx
import httpx

# Ensure DATABASE_URL is set before app imports.
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webagency_test")

from app.services.resend import ResendClient


@respx.mock
def test_send_email_posts_to_resend_and_returns_status():
    """send_email posts to Resend API and returns {"id": ..., "status": "sent"}."""
    respx.post("https://api.resend.com/emails").mock(
        return_value=httpx.Response(200, json={"id": "email-abc-123"})
    )
    client = ResendClient(api_key="test-key")
    result = client.send_email(
        to="owner@mikesplumbing.com",
        subject="I built Mike's Plumbing a website",
        business_name="Mike's Plumbing",
        city="Toronto",
        site_url="https://mikes-plumbing-toronto.vercel.app",
    )
    assert result["status"] == "sent"
    assert result["id"] == "email-abc-123"


@respx.mock
def test_send_email_uses_bearer_auth():
    """send_email uses Bearer token authorisation header."""
    route = respx.post("https://api.resend.com/emails").mock(
        return_value=httpx.Response(200, json={"id": "abc"})
    )
    client = ResendClient(api_key="my-secret-key")
    client.send_email(
        to="owner@example.com",
        subject="Test",
        business_name="Test Biz",
        city="Toronto",
        site_url="https://test.vercel.app",
    )
    assert route.called
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer my-secret-key"


@respx.mock
def test_send_email_raises_on_http_error():
    """send_email raises an exception when Resend returns a non-2xx status."""
    respx.post("https://api.resend.com/emails").mock(
        return_value=httpx.Response(422, json={"error": "invalid"})
    )
    client = ResendClient(api_key="test-key")
    with pytest.raises(httpx.HTTPStatusError):
        client.send_email(
            to="bad@example.com",
            subject="Test",
            business_name="Biz",
            city="City",
            site_url="https://example.vercel.app",
        )


@respx.mock
def test_send_email_interpolates_template_with_custom_source():
    """send_email uses the ``source`` parameter in the HTML body."""
    route = respx.post("https://api.resend.com/emails").mock(
        return_value=httpx.Response(200, json={"id": "x"})
    )
    client = ResendClient(api_key="key")
    client.send_email(
        to="a@b.com",
        subject="Sub",
        business_name="My Salon",
        city="Vancouver",
        site_url="https://salon.vercel.app",
        source="Yelp",
    )
    request = route.calls.last.request
    import json
    body = json.loads(request.content)
    assert "Yelp" in body["html"]
