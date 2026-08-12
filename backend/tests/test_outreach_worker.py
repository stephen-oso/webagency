"""Tests for outreach_task — fully mock-based, no PostgreSQL required."""

import inspect
import os
import uuid
from unittest.mock import patch, MagicMock, call

import pytest
import celery.exceptions

# Ensure DATABASE_URL is set before any app module imports.
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webagency_test")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_business(**kwargs) -> MagicMock:
    b = MagicMock()
    b.id = kwargs.get("id", uuid.uuid4())
    b.name = kwargs.get("name", "Mike's Plumbing")
    b.city = kwargs.get("city", "Toronto")
    b.state = kwargs.get("state", "ON")
    b.email = kwargs.get("email", "mike@mikesplumbing.com")
    b.category = kwargs.get("category", "plumber")
    b.existing_website = kwargs.get("existing_website", None)
    b.status = kwargs.get("status", "published")
    return b


def _make_site(business_id=None, **kwargs) -> MagicMock:
    s = MagicMock()
    s.id = kwargs.get("id", uuid.uuid4())
    s.business_id = business_id or uuid.uuid4()
    s.vercel_url = kwargs.get("vercel_url", "https://mikes-plumbing-toronto.vercel.app")
    s.custom_subdomain = kwargs.get("custom_subdomain", None)
    s.review_status = kwargs.get("review_status", "approved")
    return s


def _make_mock_db(business, site, outreach_count=0):
    """Return a mock SQLAlchemy session whose query calls return the given objects."""
    mock_db = MagicMock()

    # _count_todays_outreach does: db.query(Outreach).filter(...).count()
    # outreach_task does: db.query(Business).filter(...).first()
    # outreach_task does: db.query(Site).filter(...).first()
    # We need to distinguish between count() and first() calls.

    query_mock_outreach = MagicMock()
    query_mock_outreach.filter.return_value.count.return_value = outreach_count

    query_mock_business = MagicMock()
    query_mock_business.filter.return_value.first.return_value = business

    query_mock_site = MagicMock()
    query_mock_site.filter.return_value.first.return_value = site

    # db.query() is called with a model class — use side_effect to dispatch.
    from app.models.outreach import Outreach
    from app.models.business import Business
    from app.models.site import Site

    def _query_dispatch(model):
        if model is Outreach:
            return query_mock_outreach
        if model is Business:
            return query_mock_business
        if model is Site:
            return query_mock_site
        return MagicMock()

    mock_db.query.side_effect = _query_dispatch
    mock_db.flush.return_value = None
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.rollback.return_value = None
    mock_db.close.return_value = None
    return mock_db


def _run_outreach_task(
    business_id: str,
    site_id: str,
    mock_db,
    resend_return=None,
    form_return=True,
    hunter_api_key=None,
    resend_raises=None,
):
    """Run outreach_task.run() with all external deps patched."""
    resend_return = resend_return or {"id": "email-123", "status": "sent"}

    with patch("app.workers.outreach_worker.ResendClient") as MockResend, \
         patch("app.workers.outreach_worker.FormOutreachClient") as MockForm, \
         patch("app.workers.outreach_worker.HunterClient") as MockHunter, \
         patch("app.workers.outreach_worker.SessionLocal", return_value=mock_db), \
         patch("app.workers.outreach_worker.settings") as mock_settings:

        mock_settings.outreach_daily_cap = 20
        mock_settings.resend_api_key = "resend-test-key"
        mock_settings.hunter_api_key = hunter_api_key

        if resend_raises:
            MockResend.return_value.send_email.side_effect = resend_raises
        else:
            MockResend.return_value.send_email.return_value = resend_return

        MockForm.return_value.submit_form.return_value = form_return
        MockHunter.return_value.find_email.return_value = None

        from app.workers.outreach_worker import outreach_task
        outreach_task.run(business_id, site_id)

    return MockResend, MockForm, MockHunter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_outreach_sends_email_when_business_email_available():
    """outreach_task calls send_email when business.email is set."""
    business = _make_business(email="mike@mikesplumbing.com")
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    MockResend, _, _ = _run_outreach_task(str(business.id), str(site.id), mock_db)

    MockResend.return_value.send_email.assert_called_once()
    call_kwargs = MockResend.return_value.send_email.call_args[1]
    assert call_kwargs["to"] == "mike@mikesplumbing.com"


def test_outreach_sets_email_status_sent_on_success():
    """outreach_task sets record.email_status = 'sent' after successful send."""
    business = _make_business(email="mike@mikesplumbing.com")
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    outreach_records_added = []
    original_add = mock_db.add.side_effect

    def capture_add(obj):
        from app.models.outreach import Outreach
        if isinstance(obj, Outreach):
            outreach_records_added.append(obj)

    mock_db.add.side_effect = capture_add

    _run_outreach_task(str(business.id), str(site.id), mock_db)

    assert len(outreach_records_added) >= 1
    outreach_row = outreach_records_added[0]
    assert outreach_row.email_status == "sent"


def test_outreach_sets_email_status_failed_when_send_raises():
    """outreach_task sets record.email_status = 'failed' when send_email raises."""
    business = _make_business(email="mike@mikesplumbing.com")
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    outreach_records_added = []

    def capture_add(obj):
        from app.models.outreach import Outreach
        if isinstance(obj, Outreach):
            outreach_records_added.append(obj)

    mock_db.add.side_effect = capture_add

    _run_outreach_task(
        str(business.id), str(site.id), mock_db,
        resend_raises=Exception("SMTP error"),
    )

    assert outreach_records_added[0].email_status == "failed"


def test_outreach_skips_email_when_no_email_available():
    """outreach_task sets record.email_status = 'skipped' when no email can be found."""
    business = _make_business(email=None, existing_website=None)
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    outreach_records_added = []

    def capture_add(obj):
        from app.models.outreach import Outreach
        if isinstance(obj, Outreach):
            outreach_records_added.append(obj)

    mock_db.add.side_effect = capture_add

    _run_outreach_task(str(business.id), str(site.id), mock_db)

    assert outreach_records_added[0].email_status == "skipped"


def test_outreach_sets_form_status_submitted_on_success():
    """outreach_task sets record.form_status = 'submitted' when form submit returns True."""
    business = _make_business(existing_website="https://mikesplumbing.com")
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    outreach_records_added = []

    def capture_add(obj):
        from app.models.outreach import Outreach
        if isinstance(obj, Outreach):
            outreach_records_added.append(obj)

    mock_db.add.side_effect = capture_add

    _run_outreach_task(
        str(business.id), str(site.id), mock_db, form_return=True
    )

    assert outreach_records_added[0].form_status == "submitted"


def test_outreach_sets_form_status_failed_when_form_returns_false():
    """outreach_task sets record.form_status = 'failed' when submit_form returns False."""
    business = _make_business(existing_website="https://mikesplumbing.com")
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    outreach_records_added = []

    def capture_add(obj):
        from app.models.outreach import Outreach
        if isinstance(obj, Outreach):
            outreach_records_added.append(obj)

    mock_db.add.side_effect = capture_add

    _run_outreach_task(
        str(business.id), str(site.id), mock_db, form_return=False
    )

    assert outreach_records_added[0].form_status == "failed"


def test_outreach_sets_form_status_skipped_when_no_existing_website():
    """outreach_task sets record.form_status = 'skipped' when no existing website."""
    business = _make_business(existing_website=None)
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    outreach_records_added = []

    def capture_add(obj):
        from app.models.outreach import Outreach
        if isinstance(obj, Outreach):
            outreach_records_added.append(obj)

    mock_db.add.side_effect = capture_add

    _run_outreach_task(str(business.id), str(site.id), mock_db)

    assert outreach_records_added[0].form_status == "skipped"


def test_outreach_sets_business_status_to_outreached():
    """outreach_task sets business.status = 'outreached' on completion."""
    business = _make_business(email="mike@example.com")
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    _run_outreach_task(str(business.id), str(site.id), mock_db)

    assert business.status == "outreached"


def test_outreach_commits_db():
    """outreach_task calls db.commit() after successful processing."""
    business = _make_business(email="mike@example.com")
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    _run_outreach_task(str(business.id), str(site.id), mock_db)

    mock_db.commit.assert_called_once()


def test_outreach_adds_job_record():
    """outreach_task adds a Job with step='outreach' and status='success'."""
    from app.models.job import Job

    business = _make_business(email="mike@example.com")
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    added_objects = []
    mock_db.add.side_effect = lambda obj: added_objects.append(obj)

    _run_outreach_task(str(business.id), str(site.id), mock_db)

    job_objects = [o for o in added_objects if isinstance(o, Job)]
    assert len(job_objects) == 1
    assert job_objects[0].step == "outreach"
    assert job_objects[0].status == "success"


def test_outreach_respects_daily_cap():
    """outreach_task raises Retry when daily cap is reached."""
    business = _make_business()
    site = _make_site(business_id=business.id)
    # outreach_count == outreach_daily_cap triggers the cap.
    mock_db = _make_mock_db(business, site, outreach_count=20)

    with patch("app.workers.outreach_worker.SessionLocal", return_value=mock_db), \
         patch("app.workers.outreach_worker.settings") as mock_settings:
        mock_settings.outreach_daily_cap = 20

        from app.workers.outreach_worker import outreach_task
        with pytest.raises(celery.exceptions.Retry):
            outreach_task.run(str(business.id), str(site.id))

    # Nothing should have been written to the DB.
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


def test_outreach_skips_when_business_not_found():
    """outreach_task returns silently when business is not found."""
    site = _make_site()
    mock_db = _make_mock_db(business=None, site=site, outreach_count=0)

    MockResend, MockForm, _ = _run_outreach_task(
        str(uuid.uuid4()), str(site.id), mock_db
    )

    MockResend.return_value.send_email.assert_not_called()
    MockForm.return_value.submit_form.assert_not_called()


def test_outreach_uses_hunter_when_no_email_but_has_website():
    """outreach_task uses HunterClient to look up email when business.email is None."""
    business = _make_business(email=None, existing_website="https://mikesplumbing.com")
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    with patch("app.workers.outreach_worker.ResendClient") as MockResend, \
         patch("app.workers.outreach_worker.FormOutreachClient") as MockForm, \
         patch("app.workers.outreach_worker.HunterClient") as MockHunter, \
         patch("app.workers.outreach_worker.SessionLocal", return_value=mock_db), \
         patch("app.workers.outreach_worker.settings") as mock_settings:

        mock_settings.outreach_daily_cap = 20
        mock_settings.resend_api_key = "resend-key"
        mock_settings.hunter_api_key = "hunter-key"

        MockHunter.return_value.find_email.return_value = "hunter@mikesplumbing.com"
        MockResend.return_value.send_email.return_value = {"id": "x", "status": "sent"}
        MockForm.return_value.submit_form.return_value = False

        from app.workers.outreach_worker import outreach_task
        outreach_task.run(str(business.id), str(site.id))

    MockHunter.assert_called_once()
    send_call = MockResend.return_value.send_email.call_args[1]
    assert send_call["to"] == "hunter@mikesplumbing.com"


def test_outreach_uses_exponential_backoff_on_retry():
    """outreach_task must use countdown= in self.retry(), not default_retry_delay on decorator."""
    from app.workers import outreach_worker

    source = inspect.getsource(outreach_worker.outreach_task)
    assert "default_retry_delay" not in source, (
        "outreach_task must NOT use default_retry_delay; use countdown= in self.retry()"
    )
    assert "countdown=60 * (2 ** self.request.retries)" in source, (
        "outreach_task must use exponential backoff: countdown=60 * (2 ** self.request.retries)"
    )


def test_outreach_subject_includes_business_name():
    """outreach_task uses the correct email subject line format."""
    business = _make_business(name="Sunny Cafe", email="hi@sunnycafe.com")
    site = _make_site(business_id=business.id)
    mock_db = _make_mock_db(business, site, outreach_count=0)

    with patch("app.workers.outreach_worker.ResendClient") as MockResend, \
         patch("app.workers.outreach_worker.FormOutreachClient"), \
         patch("app.workers.outreach_worker.HunterClient"), \
         patch("app.workers.outreach_worker.SessionLocal", return_value=mock_db), \
         patch("app.workers.outreach_worker.settings") as mock_settings:

        mock_settings.outreach_daily_cap = 20
        mock_settings.resend_api_key = "key"
        mock_settings.hunter_api_key = None
        MockResend.return_value.send_email.return_value = {"id": "x", "status": "sent"}

        from app.workers.outreach_worker import outreach_task
        outreach_task.run(str(business.id), str(site.id))

    send_kwargs = MockResend.return_value.send_email.call_args[1]
    assert "Sunny Cafe" in send_kwargs["subject"]
    assert "take a look" in send_kwargs["subject"]
