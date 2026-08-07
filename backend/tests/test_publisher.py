"""Tests for the Publisher interface and VercelPublisher implementation."""
import os
import pytest
from unittest.mock import patch, MagicMock

# Set DATABASE_URL before any app module imports so pydantic-settings can initialise.
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webagency_test")

from app.services.publisher import VercelPublisher


def test_vercel_publisher_calls_cli_and_returns_url(tmp_path):
    """VercelPublisher.deploy calls 'vercel deploy' and returns the last line of stdout."""
    publisher = VercelPublisher(token="tok-abc", team_id=None, agency_domain="youragency.com")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Building...\nhttps://mikes-plumbing-toronto.vercel.app"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        url = publisher.deploy(str(tmp_path), "mikes-plumbing-toronto")

    assert url == "https://mikes-plumbing-toronto.vercel.app"
    cmd = mock_run.call_args[0][0]
    assert "vercel" in cmd
    assert "deploy" in cmd
    assert "--token" in cmd
    assert "tok-abc" in cmd


def test_vercel_publisher_includes_prod_or_yes_flag(tmp_path):
    """VercelPublisher.deploy passes --yes (or --prod) to skip prompts."""
    publisher = VercelPublisher(token="tok-abc", team_id=None, agency_domain="youragency.com")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "https://mikes-plumbing-toronto.vercel.app"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        publisher.deploy(str(tmp_path), "mikes-plumbing-toronto")

    cmd = mock_run.call_args[0][0]
    assert "--yes" in cmd or "--prod" in cmd


def test_vercel_publisher_includes_scope_when_team_id_set(tmp_path):
    """VercelPublisher.deploy passes --scope {team_id} when team_id is set."""
    publisher = VercelPublisher(token="tok-abc", team_id="my-team", agency_domain="youragency.com")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "https://example.vercel.app"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        publisher.deploy(str(tmp_path), "some-slug")

    cmd = mock_run.call_args[0][0]
    assert "--scope" in cmd
    assert "my-team" in cmd


def test_vercel_publisher_no_scope_when_team_id_none(tmp_path):
    """VercelPublisher.deploy does NOT pass --scope when team_id is None."""
    publisher = VercelPublisher(token="tok-abc", team_id=None, agency_domain="youragency.com")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "https://example.vercel.app"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        publisher.deploy(str(tmp_path), "some-slug")

    cmd = mock_run.call_args[0][0]
    assert "--scope" not in cmd


def test_vercel_publisher_raises_on_failure(tmp_path):
    """VercelPublisher.deploy raises RuntimeError when vercel CLI returns non-zero exit code."""
    publisher = VercelPublisher(token="tok-abc", team_id=None, agency_domain="youragency.com")

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Error: Not authenticated"

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="Vercel deploy failed"):
            publisher.deploy(str(tmp_path), "some-slug")


def test_vercel_publisher_returns_last_line_of_stdout(tmp_path):
    """VercelPublisher.deploy returns the last non-empty line of stdout as the URL."""
    publisher = VercelPublisher(token="tok-abc", team_id=None, agency_domain="youragency.com")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Line 1\nLine 2\nhttps://final-url.vercel.app\n"

    with patch("subprocess.run", return_value=mock_result):
        url = publisher.deploy(str(tmp_path), "some-slug")

    assert url == "https://final-url.vercel.app"
