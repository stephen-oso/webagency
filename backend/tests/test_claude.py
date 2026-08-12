"""Tests for the Claude copy generation service."""

import pytest
import anthropic
from unittest.mock import patch, MagicMock
from app.services.claude import ClaudeClient


@pytest.fixture
def client():
    return ClaudeClient(api_key="test-anthropic-key")


def test_select_template_maps_categories(client):
    assert client.select_template("plumber") == "plumber"
    assert client.select_template("salon") == "salon"
    assert client.select_template("auto") == "auto"
    assert client.select_template("unknown_category") == "professional"


def test_select_template_maps_aliases(client):
    assert client.select_template("cafe") == "restaurant"
    assert client.select_template("plumbing") == "plumber"
    assert client.select_template("hair") == "salon"
    assert client.select_template("dental") == "dentist"
    assert client.select_template("lawn") == "landscaping"
    assert client.select_template("boutique") == "retail"
    assert client.select_template("contractor") == "trades"
    assert client.select_template("handyman") == "trades"
    assert client.select_template("mechanic") == "auto"
    assert client.select_template("fitness") == "gym"
    assert client.select_template("photographer") == "photography"
    assert client.select_template("realtor") == "realestate"
    assert client.select_template("daycare") == "childcare"
    assert client.select_template("vet") == "petservices"
    assert client.select_template("grooming") == "petservices"


def test_select_template_case_insensitive(client):
    assert client.select_template("PLUMBER") == "plumber"
    assert client.select_template("Salon") == "salon"
    assert client.select_template("  dentist  ") == "dentist"


def test_generate_site_copy_returns_required_keys(client):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"headline": "Toronto\'s Trusted Plumber", "subheadline": "Fast plumbing repairs in Toronto, ON.", "about": "Mike\'s Plumbing has served Toronto for 15 years.", "services": ["Leak Repair", "Drain Cleaning", "Water Heater"], "cta_text": "Get a Free Quote", "meta_description": "Mike\'s Plumbing — fast, reliable plumbing in Toronto."}')]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        result = client.generate_site_copy(
            {"name": "Mike's Plumbing", "city": "Toronto", "state": "ON", "category": "plumber"},
            {"description": "15 years of service", "services": ["Leak Repair"], "rating": 4.5, "review_count": 38, "hours": {}},
        )

    assert "headline" in result
    assert "subheadline" in result
    assert "about" in result
    assert "services" in result
    assert "cta_text" in result
    assert "meta_description" in result
    assert isinstance(result["services"], list)


def test_generate_site_copy_strips_markdown_fences(client):
    """Verify that Claude responses wrapped in ```json fences are parsed correctly."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='```json\n{"headline": "Best Salon in Austin", "subheadline": "Hair care in Austin, TX.", "about": "Luxe Hair has styled Austin since 2010.", "services": ["Cuts", "Color", "Blowouts"], "cta_text": "Book Now", "meta_description": "Luxe Hair — Austin\'s premier salon."}\n```')]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        result = client.generate_site_copy(
            {"name": "Luxe Hair", "city": "Austin", "state": "TX", "category": "salon"},
            {"description": "Premier salon", "services": ["Cuts", "Color"], "rating": 4.8, "review_count": 120, "hours": {}},
        )

    assert result["headline"] == "Best Salon in Austin"
    assert isinstance(result["services"], list)


def test_generate_site_copy_handles_missing_asset_fields(client):
    """Verify generate_site_copy handles None/missing asset fields gracefully."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"headline": "Top Auto Shop", "subheadline": "Auto repairs in Denver, CO.", "about": "Quality auto service.", "services": ["Oil Change"], "cta_text": "Call Us", "meta_description": "Auto repairs in Denver."}')]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        result = client.generate_site_copy(
            {"name": "Dave's Auto", "city": "Denver", "state": "CO", "category": "auto"},
            {},  # empty assets — all fields missing
        )

    assert "headline" in result


def test_generate_site_copy_uses_correct_model(client):
    """Verify that generate_site_copy calls Claude with the correct model string."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"headline": "h", "subheadline": "s", "about": "a", "services": [], "cta_text": "c", "meta_description": "m"}')]

    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_create = MockAnthropic.return_value.messages.create
        mock_create.return_value = mock_response
        client.generate_site_copy(
            {"name": "Test Biz", "city": "NYC", "state": "NY", "category": "retail"},
            {"description": "A shop", "services": [], "rating": 4.0, "review_count": 10, "hours": {}},
        )

    call_kwargs = mock_create.call_args
    assert call_kwargs.kwargs["model"] == "claude-sonnet-4-6"


def test_generate_site_copy_raises_on_malformed_json(client):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="this is not json")]
    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        with pytest.raises(ValueError, match="Claude returned invalid JSON"):
            client.generate_site_copy(
                {"name": "Test", "city": "Toronto", "state": "ON", "category": "plumber"},
                {},
            )


def test_generate_site_copy_raises_on_api_error(client):
    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())
        with pytest.raises(RuntimeError, match="Claude API error"):
            client.generate_site_copy(
                {"name": "Test", "city": "Toronto", "state": "ON", "category": "plumber"},
                {},
            )
