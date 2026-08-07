"""Tests for FormOutreachClient — all Playwright calls are mocked."""

import os
from unittest.mock import patch, MagicMock

# Ensure DATABASE_URL is set before app imports.
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webagency_test")

from app.services.form_outreach import FormOutreachClient


def _make_mock_page(has_textarea=True, has_submit=True):
    """Build a realistic mock Playwright page object."""
    mock_page = MagicMock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.wait_for_timeout.return_value = None

    def _query_selector(selector):
        if "textarea" in selector:
            return MagicMock() if has_textarea else None
        if "submit" in selector:
            return MagicMock() if has_submit else None
        # name/email/contact links: return None by default (fine)
        return None

    mock_page.query_selector.side_effect = _query_selector
    return mock_page


def _patch_playwright(mock_page):
    """Context manager: patch sync_playwright to return mock_page."""
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_p = MagicMock()
    mock_p.chromium.launch.return_value = mock_browser

    mock_pw_cm = MagicMock()
    mock_pw_cm.__enter__ = MagicMock(return_value=mock_p)
    mock_pw_cm.__exit__ = MagicMock(return_value=False)

    return patch("app.services.form_outreach.sync_playwright", return_value=mock_pw_cm)


def test_submit_form_returns_true_when_form_found_and_submitted():
    """submit_form returns True when a textarea and submit button are present."""
    mock_page = _make_mock_page(has_textarea=True, has_submit=True)

    with _patch_playwright(mock_page):
        client = FormOutreachClient()
        result = client.submit_form(
            "https://example.com", "Mike's Plumbing", "https://mikes.vercel.app"
        )

    assert result is True


def test_submit_form_returns_false_when_no_textarea():
    """submit_form returns False when no textarea is found."""
    mock_page = _make_mock_page(has_textarea=False, has_submit=True)

    with _patch_playwright(mock_page):
        client = FormOutreachClient()
        result = client.submit_form(
            "https://example.com", "Salon", "https://salon.vercel.app"
        )

    assert result is False


def test_submit_form_returns_false_when_no_submit_button():
    """submit_form returns False when textarea exists but no submit button."""
    mock_page = _make_mock_page(has_textarea=True, has_submit=False)

    with _patch_playwright(mock_page):
        client = FormOutreachClient()
        result = client.submit_form(
            "https://example.com", "Bakery", "https://bakery.vercel.app"
        )

    assert result is False


def test_submit_form_returns_false_on_playwright_error():
    """submit_form returns False (does not raise) when sync_playwright throws."""
    with patch(
        "app.services.form_outreach.sync_playwright",
        side_effect=Exception("browser error"),
    ):
        client = FormOutreachClient()
        result = client.submit_form(
            "https://example.com", "Salon", "https://salon.vercel.app"
        )

    assert result is False


def test_submit_form_fills_textarea_with_message():
    """submit_form calls textarea.fill() with a message containing the site URL."""
    mock_textarea = MagicMock()
    mock_page = MagicMock()
    mock_page.goto.return_value = None
    mock_page.wait_for_timeout.return_value = None

    def _query_selector(selector):
        if "textarea" in selector:
            return mock_textarea
        if "submit" in selector:
            return MagicMock()
        return None

    mock_page.query_selector.side_effect = _query_selector

    with _patch_playwright(mock_page):
        client = FormOutreachClient()
        client.submit_form(
            "https://example.com", "Mike's Plumbing", "https://mikes.vercel.app"
        )

    fill_call_args = mock_textarea.fill.call_args[0][0]
    assert "https://mikes.vercel.app" in fill_call_args
    assert "Mike's Plumbing" in fill_call_args
