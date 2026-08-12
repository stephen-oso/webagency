"""Tests for the publish worker — fully mock-based, no PostgreSQL required."""
import inspect
import json
import os
import uuid
from unittest.mock import patch, MagicMock, call

import pytest

# Set DATABASE_URL before any app module imports so pydantic-settings can initialise.
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webagency_test")


def _make_business(business_id=None, **kwargs):
    """Return a mock Business object."""
    b = MagicMock()
    b.id = uuid.UUID(business_id) if business_id else uuid.uuid4()
    b.name = kwargs.get("name", "Mike's Plumbing")
    b.city = kwargs.get("city", "Toronto")
    b.state = kwargs.get("state", "ON")
    b.category = kwargs.get("category", "plumber")
    b.status = kwargs.get("status", "built")
    return b


def _make_site(business_id=None, **kwargs):
    """Return a mock Site object."""
    s = MagicMock()
    s.id = uuid.uuid4()
    s.business_id = business_id or uuid.uuid4()
    s.template_used = kwargs.get("template_used", "plumber")
    s.review_status = kwargs.get("review_status", "pending")
    s.vercel_url = kwargs.get("vercel_url", None)
    s.custom_subdomain = kwargs.get("custom_subdomain", None)
    s.deployed_at = kwargs.get("deployed_at", None)
    return s


def _run_publish_task(business_id, mock_business, mock_site, tmp_path,
                      review_mode=True, vercel_url="https://test.vercel.app",
                      write_site_data=True):
    """Helper: patch all external deps and run publish_task.run()."""
    if write_site_data:
        build_dir = tmp_path / "built_sites" / business_id
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "site_data.json").write_text(json.dumps({
            "business_id": business_id,
            "template": mock_site.template_used,
            "copy": {},
            "photos": [],
            "business_data": {"name": mock_business.name},
        }))

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_business,  # first query: Business
        mock_site,      # second query: Site
    ]

    mock_outreach = MagicMock()

    with patch("app.workers.publish.VercelPublisher") as MockPublisher, \
         patch("app.workers.publish.SessionLocal", return_value=mock_db), \
         patch("app.workers.publish.settings") as mock_settings, \
         patch("app.workers.outreach_worker.outreach_task", mock_outreach):

        MockPublisher.return_value.deploy.return_value = vercel_url
        mock_settings.review_mode = review_mode
        mock_settings.vercel_token = "tok-test"
        mock_settings.vercel_team_id = None
        mock_settings.agency_domain = "youragency.com"
        mock_settings.base_dir = str(tmp_path)

        from app.workers.publish import publish_task
        publish_task.run(business_id)

    return mock_db, mock_outreach, MockPublisher


def test_publish_sets_review_pending_when_review_mode_on(tmp_path):
    """When review_mode=True, site.review_status is set to 'pending' and outreach is NOT enqueued."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_site = _make_site(mock_business.id)

    mock_db, mock_outreach, _ = _run_publish_task(
        business_id, mock_business, mock_site, tmp_path, review_mode=True
    )

    assert mock_site.review_status == "pending"
    mock_outreach.delay.assert_not_called()


def test_publish_enqueues_outreach_when_review_mode_off(tmp_path):
    """When review_mode=False, site.review_status is set to 'approved' and outreach_task.delay is called."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id, name="City Salon", city="Vancouver", state="BC")
    mock_site = _make_site(mock_business.id)

    mock_db, mock_outreach, _ = _run_publish_task(
        business_id, mock_business, mock_site, tmp_path, review_mode=False
    )

    assert mock_site.review_status == "approved"
    mock_outreach.delay.assert_called_once()
    call_args = mock_outreach.delay.call_args[0]
    assert call_args[0] == business_id
    assert call_args[1] == str(mock_site.id)


def test_publish_sets_vercel_url(tmp_path):
    """publish_task sets site.vercel_url to the URL returned by the publisher."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_site = _make_site(mock_business.id)
    expected_url = "https://mikes-plumbing-abc12345.vercel.app"

    _run_publish_task(
        business_id, mock_business, mock_site, tmp_path,
        vercel_url=expected_url
    )

    assert mock_site.vercel_url == expected_url


def test_publish_sets_custom_subdomain(tmp_path):
    """publish_task sets site.custom_subdomain to '{slug}.{agency_domain}'."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id, name="Top Plumbing")
    mock_site = _make_site(mock_business.id)

    _run_publish_task(business_id, mock_business, mock_site, tmp_path)

    expected_id_prefix = str(mock_business.id)[:8]
    expected_slug = f"top-plumbing-{expected_id_prefix}"
    assert mock_site.custom_subdomain == f"{expected_slug}.youragency.com"


def test_publish_sets_deployed_at(tmp_path):
    """publish_task sets site.deployed_at to a non-None datetime."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_site = _make_site(mock_business.id)

    _run_publish_task(business_id, mock_business, mock_site, tmp_path)

    assert mock_site.deployed_at is not None


def test_publish_updates_business_status_to_published(tmp_path):
    """publish_task sets business.status to 'published'."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_site = _make_site(mock_business.id)

    _run_publish_task(business_id, mock_business, mock_site, tmp_path)

    assert mock_business.status == "published"


def test_publish_adds_job_record(tmp_path):
    """publish_task calls db.add() with a Job having step='publish' and status='success'."""
    from app.models.job import Job

    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_site = _make_site(mock_business.id)

    mock_db, _, _ = _run_publish_task(business_id, mock_business, mock_site, tmp_path)

    added_objects = [c.args[0] for c in mock_db.add.call_args_list]
    job_objects = [o for o in added_objects if isinstance(o, Job)]
    assert len(job_objects) == 1
    assert job_objects[0].step == "publish"
    assert job_objects[0].status == "success"


def test_publish_commits_db(tmp_path):
    """publish_task calls db.commit() after setting all fields."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_site = _make_site(mock_business.id)

    mock_db, _, _ = _run_publish_task(business_id, mock_business, mock_site, tmp_path)

    mock_db.commit.assert_called_once()


def test_publish_skips_missing_business(tmp_path):
    """publish_task returns silently when Business is not found."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_outreach = MagicMock()

    with patch("app.workers.publish.VercelPublisher") as MockPublisher, \
         patch("app.workers.publish.SessionLocal", return_value=mock_db), \
         patch("app.workers.publish.settings") as mock_settings, \
         patch("app.workers.outreach_worker.outreach_task", mock_outreach):

        mock_settings.base_dir = str(tmp_path)

        from app.workers.publish import publish_task
        publish_task.run(str(uuid.uuid4()))

    MockPublisher.return_value.deploy.assert_not_called()
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


def test_publish_skips_missing_site(tmp_path):
    """publish_task returns silently when Site record is not found."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_outreach = MagicMock()

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_business,  # Business found
        None,           # Site not found
    ]

    with patch("app.workers.publish.VercelPublisher") as MockPublisher, \
         patch("app.workers.publish.SessionLocal", return_value=mock_db), \
         patch("app.workers.publish.settings") as mock_settings, \
         patch("app.workers.outreach_worker.outreach_task", mock_outreach):

        mock_settings.base_dir = str(tmp_path)

        from app.workers.publish import publish_task
        publish_task.run(business_id)

    MockPublisher.return_value.deploy.assert_not_called()
    mock_db.add.assert_not_called()


def test_publish_uses_exponential_backoff_on_retry():
    """publish_task must use countdown= in self.retry(), not default_retry_delay on the decorator."""
    from app.workers import publish

    source = inspect.getsource(publish.publish_task)
    assert "default_retry_delay" not in source, (
        "publish_task must NOT use default_retry_delay; use countdown= in self.retry()"
    )
    assert "countdown=60 * (2 ** self.request.retries)" in source, (
        "publish_task must use exponential backoff: countdown=60 * (2 ** self.request.retries)"
    )


def test_publish_slug_uses_name_and_id_prefix(tmp_path):
    """Business slug is '{name}-{id[:8]}' with spaces replaced by hyphens."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id, name="Top Notch Landscaping")
    mock_site = _make_site(mock_business.id)

    _, _, MockPublisher = _run_publish_task(
        business_id, mock_business, mock_site, tmp_path
    )

    expected_id_prefix = str(mock_business.id)[:8]
    expected_slug = f"top-notch-landscaping-{expected_id_prefix}"
    deploy_call_slug = MockPublisher.return_value.deploy.call_args[0][1]
    assert deploy_call_slug == expected_slug


def test_publish_passes_build_dir_to_deploy(tmp_path):
    """publish_task passes the correct build directory path to publisher.deploy()."""
    business_id = str(uuid.uuid4())
    mock_business = _make_business(business_id)
    mock_site = _make_site(mock_business.id)

    _, _, MockPublisher = _run_publish_task(
        business_id, mock_business, mock_site, tmp_path
    )

    deploy_call_build_path = MockPublisher.return_value.deploy.call_args[0][0]
    expected_path = str(tmp_path / "built_sites" / business_id)
    assert deploy_call_build_path == expected_path
