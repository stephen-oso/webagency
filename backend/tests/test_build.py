"""Tests for the build worker — fully mock-based, no PostgreSQL required."""
import json
import uuid
import inspect
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

# Set DATABASE_URL before any app module imports so pydantic-settings can initialise.
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webagency_test")


MOCK_COPY = {
    "headline": "Vancouver's Top Salon",
    "subheadline": "Expert cuts and color in Vancouver, BC.",
    "about": "City Salon has been styling Vancouver since 2010.",
    "services": ["Haircut", "Color", "Blowout"],
    "cta_text": "Book Now",
    "meta_description": "City Salon — expert hair in Vancouver.",
}


def _make_business(business_id=None, **kwargs):
    """Return a mock Business object."""
    b = MagicMock()
    b.id = uuid.UUID(business_id) if business_id else uuid.uuid4()
    b.name = kwargs.get("name", "City Salon")
    b.city = kwargs.get("city", "Vancouver")
    b.state = kwargs.get("state", "BC")
    b.phone = kwargs.get("phone", "604-555-0100")
    b.email = kwargs.get("email", None)
    b.category = kwargs.get("category", "salon")
    b.status = kwargs.get("status", "gathering_done")
    return b


def _make_asset(**kwargs):
    """Return a mock BusinessAsset object."""
    a = MagicMock()
    a.photos = kwargs.get("photos", ["https://r2.example.com/photo.jpg"])
    a.description = kwargs.get("description", "Top salon in Vancouver")
    a.hours = kwargs.get("hours", None)
    a.rating = kwargs.get("rating", 4.8)
    a.review_count = kwargs.get("review_count", 200)
    a.services = kwargs.get("services", ["Haircut", "Color"])
    a.price_range = kwargs.get("price_range", "$$")
    return a


def _run_build_task(business_id, mock_business, mock_asset, tmp_path, copy=None, template="salon"):
    """Helper: patch all external deps and run build_task.run()."""
    copy = copy or MOCK_COPY
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_business,   # first call: Business
        mock_asset,      # second call: BusinessAsset
    ]
    mock_publish = MagicMock()

    with patch("app.workers.build.ClaudeClient") as MockClaude, \
         patch("app.workers.build.SessionLocal", return_value=mock_db), \
         patch("app.workers.build.settings") as mock_settings, \
         patch("app.workers.publish.publish_task", mock_publish):

        mock_settings.anthropic_api_key = "test-key"
        mock_settings.base_dir = str(tmp_path)

        MockClaude.return_value.select_template.return_value = template
        MockClaude.return_value.generate_site_copy.return_value = copy

        from app.workers.build import build_task
        build_task.run(str(mock_business.id))

    return mock_db, mock_publish


def test_build_creates_site_data_json(tmp_path):
    """build_task writes a site_data.json manifest to built_sites/{business_id}/."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_asset = _make_asset()

    _run_build_task(business_id, mock_business, mock_asset, tmp_path)

    site_data_path = tmp_path / "built_sites" / business_id / "site_data.json"
    assert site_data_path.exists(), "site_data.json was not created"

    data = json.loads(site_data_path.read_text())
    assert data["business_id"] == business_id
    assert data["template"] == "salon"
    assert data["copy"] == MOCK_COPY
    assert data["photos"] == ["https://r2.example.com/photo.jpg"]
    assert data["business_data"]["name"] == "City Salon"
    assert data["business_data"]["city"] == "Vancouver"
    assert data["business_data"]["state"] == "BC"


def test_build_site_data_json_structure(tmp_path):
    """site_data.json contains all required top-level keys."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_asset = _make_asset()

    _run_build_task(business_id, mock_business, mock_asset, tmp_path)

    data = json.loads((tmp_path / "built_sites" / business_id / "site_data.json").read_text())
    for key in ("business_id", "template", "copy", "photos", "business_data"):
        assert key in data, f"Missing key: {key}"
    for key in ("name", "city", "state", "phone", "email", "category", "hours", "rating", "review_count"):
        assert key in data["business_data"], f"Missing business_data key: {key}"


def test_build_updates_business_status(tmp_path):
    """build_task sets Business.status to 'built'."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_asset = _make_asset()

    _run_build_task(business_id, mock_business, mock_asset, tmp_path)

    assert mock_business.status == "built"


def test_build_enqueues_publish_task(tmp_path):
    """build_task calls publish_task.delay(business_id) exactly once."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_asset = _make_asset()

    _, mock_publish = _run_build_task(business_id, mock_business, mock_asset, tmp_path)

    mock_publish.delay.assert_called_once_with(business_id)


def test_build_adds_site_to_db(tmp_path):
    """build_task calls db.add() with a Site object."""
    from app.models.site import Site

    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_asset = _make_asset()

    mock_db, _ = _run_build_task(business_id, mock_business, mock_asset, tmp_path)

    added_objects = [c.args[0] for c in mock_db.add.call_args_list]
    site_objects = [o for o in added_objects if isinstance(o, Site)]
    assert len(site_objects) == 1
    assert site_objects[0].template_used == "salon"


def test_build_adds_job_to_db(tmp_path):
    """build_task calls db.add() with a Job object having step='build' and status='success'."""
    from app.models.job import Job

    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_asset = _make_asset()

    mock_db, _ = _run_build_task(business_id, mock_business, mock_asset, tmp_path)

    added_objects = [c.args[0] for c in mock_db.add.call_args_list]
    job_objects = [o for o in added_objects if isinstance(o, Job)]
    assert len(job_objects) == 1
    assert job_objects[0].step == "build"
    assert job_objects[0].status == "success"


def test_build_skips_missing_business(tmp_path):
    """build_task returns silently when Business is not found."""
    mock_db = MagicMock()
    # query returns None for the business
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_publish = MagicMock()

    with patch("app.workers.build.ClaudeClient") as MockClaude, \
         patch("app.workers.build.SessionLocal", return_value=mock_db), \
         patch("app.workers.build.settings") as mock_settings, \
         patch("app.workers.publish.publish_task", mock_publish):

        mock_settings.anthropic_api_key = "test-key"
        mock_settings.base_dir = str(tmp_path)

        from app.workers.build import build_task
        build_task.run(str(uuid.uuid4()))

    MockClaude.assert_not_called()
    mock_publish.delay.assert_not_called()
    mock_db.add.assert_not_called()


def test_build_handles_no_assets(tmp_path):
    """build_task works when no BusinessAsset row exists (photos defaults to empty list)."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_business,  # Business found
        None,           # No asset
    ]
    mock_publish = MagicMock()

    with patch("app.workers.build.ClaudeClient") as MockClaude, \
         patch("app.workers.build.SessionLocal", return_value=mock_db), \
         patch("app.workers.build.settings") as mock_settings, \
         patch("app.workers.publish.publish_task", mock_publish):

        mock_settings.anthropic_api_key = "test-key"
        mock_settings.base_dir = str(tmp_path)

        MockClaude.return_value.select_template.return_value = "salon"
        MockClaude.return_value.generate_site_copy.return_value = MOCK_COPY

        from app.workers.build import build_task
        build_task.run(business_id)

    site_data_path = tmp_path / "built_sites" / business_id / "site_data.json"
    assert site_data_path.exists()
    data = json.loads(site_data_path.read_text())
    assert data["photos"] == []


def test_build_calls_claude_select_template(tmp_path):
    """build_task calls ClaudeClient.select_template with business.category."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id, category="dentist")
    mock_asset = _make_asset()

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_business, mock_asset]
    mock_publish = MagicMock()

    with patch("app.workers.build.ClaudeClient") as MockClaude, \
         patch("app.workers.build.SessionLocal", return_value=mock_db), \
         patch("app.workers.build.settings") as mock_settings, \
         patch("app.workers.publish.publish_task", mock_publish):

        mock_settings.anthropic_api_key = "test-key"
        mock_settings.base_dir = str(tmp_path)

        MockClaude.return_value.select_template.return_value = "dentist"
        MockClaude.return_value.generate_site_copy.return_value = MOCK_COPY

        from app.workers.build import build_task
        build_task.run(business_id)

    MockClaude.return_value.select_template.assert_called_once_with("dentist")


def test_build_uses_exponential_backoff_on_retry():
    """build_task must use countdown= in self.retry(), not default_retry_delay on the decorator."""
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webagency_test")

    from app.workers import build

    source = inspect.getsource(build.build_task)
    assert "default_retry_delay" not in source, (
        "build_task must NOT use default_retry_delay; use countdown= in self.retry()"
    )
    assert "countdown=60 * (2 ** self.request.retries)" in source, (
        "build_task must use exponential backoff: countdown=60 * (2 ** self.request.retries)"
    )


def test_build_copies_template_to_build_dir(tmp_path):
    """build_task copies the template directory into built_sites/{business_id}/."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_asset = _make_asset()

    # Create a real template stub so os.path.exists returns True naturally.
    template_dir = tmp_path / "templates" / "salon"
    template_dir.mkdir(parents=True)
    (template_dir / "index.html").write_text("<html></html>")

    with patch("app.workers.build.shutil.copytree") as mock_copytree:
        _run_build_task(business_id, mock_business, mock_asset, tmp_path, template="salon")

    assert mock_copytree.called, "shutil.copytree was not called"
    call_args = mock_copytree.call_args
    src_path = call_args.args[0]
    dst_path = call_args.args[1]

    assert src_path.endswith(os.path.join("templates", "salon")), (
        f"copytree source should end with templates/salon, got: {src_path}"
    )
    assert dst_path.endswith(os.path.join("built_sites", business_id)), (
        f"copytree destination should end with built_sites/{business_id}, got: {dst_path}"
    )
