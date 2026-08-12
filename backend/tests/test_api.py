"""
REST API endpoint tests.

All DB-touching tests mock the get_db dependency — no real PostgreSQL required.
"""
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_business(**kwargs):
    b = MagicMock()
    b.id = kwargs.get("id", uuid.uuid4())
    b.name = kwargs.get("name", "Test Biz")
    b.city = kwargs.get("city", "Toronto")
    b.state = kwargs.get("state", "ON")
    b.category = kwargs.get("category", "plumber")
    b.status = kwargs.get("status", "discovered")
    b.website_score = kwargs.get("website_score", 2)
    b.created_at = kwargs.get("created_at", datetime(2026, 1, 1))
    b.address = kwargs.get("address", None)
    b.phone = kwargs.get("phone", None)
    b.email = kwargs.get("email", None)
    b.existing_website = kwargs.get("existing_website", None)
    b.google_place_id = kwargs.get("google_place_id", None)
    b.yelp_id = kwargs.get("yelp_id", None)
    # Explicit None for nested detail fields so model_validate doesn't get MagicMock auto-attrs
    b.asset = None
    b.site = None
    b.outreach = None
    b.recent_jobs = []
    return b


def _make_site(**kwargs):
    s = MagicMock()
    s.id = kwargs.get("id", uuid.uuid4())
    s.business_id = kwargs.get("business_id", uuid.uuid4())
    s.template_used = kwargs.get("template_used", "plumber")
    s.vercel_url = kwargs.get("vercel_url", "https://test.vercel.app")
    s.custom_subdomain = kwargs.get("custom_subdomain", None)
    s.review_status = kwargs.get("review_status", "pending")
    s.deployed_at = kwargs.get("deployed_at", None)
    return s


def _make_job(**kwargs):
    j = MagicMock()
    j.id = kwargs.get("id", uuid.uuid4())
    j.business_id = kwargs.get("business_id", uuid.uuid4())
    j.step = kwargs.get("step", "gather")
    j.status = kwargs.get("status", "success")
    j.error_msg = kwargs.get("error_msg", None)
    j.attempts = kwargs.get("attempts", 1)
    j.last_run_at = kwargs.get("last_run_at", datetime(2026, 1, 1))
    return j


def _make_outreach(**kwargs):
    o = MagicMock()
    o.id = kwargs.get("id", uuid.uuid4())
    o.business_id = kwargs.get("business_id", uuid.uuid4())
    o.email_to = kwargs.get("email_to", None)
    o.email_sent_at = kwargs.get("email_sent_at", None)
    o.email_status = kwargs.get("email_status", None)
    o.form_submitted_at = kwargs.get("form_submitted_at", None)
    o.form_status = kwargs.get("form_status", None)
    o.responded_at = kwargs.get("responded_at", None)
    return o


def _mock_db():
    """Return a MagicMock session with a chainable query interface."""
    mock_session = MagicMock()
    return mock_session


def _override_db(mock_session):
    """Return a dependency-override function that yields mock_session."""
    def _override():
        yield mock_session
    return _override


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/businesses
# ---------------------------------------------------------------------------

def test_list_businesses_empty():
    mock_session = _mock_db()
    # chain: query().filter().order_by().offset().limit().all() → []
    mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    mock_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get("/api/businesses")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_businesses_returns_data():
    biz_id = uuid.uuid4()
    b = _make_business(id=biz_id, name="Plumb Co")

    mock_session = _mock_db()
    mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [b]
    mock_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [b]

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get("/api/businesses")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Plumb Co"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_businesses_filter_by_status():
    b = _make_business(status="gathering_done")

    mock_session = _mock_db()
    mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [b]

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get("/api/businesses?status=gathering_done")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "gathering_done"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# GET /api/businesses/{id}
# ---------------------------------------------------------------------------

def test_get_business_found():
    """GET /api/businesses/{id} returns nested keys; no related data → nulls/empty lists."""
    biz_id = uuid.uuid4()
    b = _make_business(id=biz_id, name="Detailed Biz")

    mock_session = _mock_db()

    def _query_side_effect(model):
        from app.models.business import Business, BusinessAsset
        from app.models.site import Site
        from app.models.outreach import Outreach
        from app.models.job import Job

        q = MagicMock()
        if model is Business:
            q.filter.return_value.first.return_value = b
        elif model is BusinessAsset:
            q.filter.return_value.first.return_value = None
        elif model is Site:
            q.filter.return_value.first.return_value = None
        elif model is Outreach:
            q.filter.return_value.first.return_value = None
        elif model is Job:
            q.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        else:
            q.filter.return_value.first.return_value = None
        return q

    mock_session.query.side_effect = _query_side_effect

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get(f"/api/businesses/{biz_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Detailed Biz"
        assert "asset" in data
        assert "site" in data
        assert "outreach" in data
        assert "recent_jobs" in data
        assert data["asset"] is None
        assert data["site"] is None
        assert data["outreach"] is None
        assert data["recent_jobs"] == []
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_get_business_found_with_site():
    """GET /api/businesses/{id} returns nested site when site exists."""
    biz_id = uuid.uuid4()
    site_id = uuid.uuid4()
    b = _make_business(id=biz_id, name="Biz With Site")
    s = _make_site(id=site_id, business_id=biz_id, review_status="pending", template_used="plumber")

    mock_session = _mock_db()

    def _query_side_effect(model):
        from app.models.business import Business, BusinessAsset
        from app.models.site import Site
        from app.models.outreach import Outreach
        from app.models.job import Job

        q = MagicMock()
        if model is Business:
            q.filter.return_value.first.return_value = b
        elif model is BusinessAsset:
            q.filter.return_value.first.return_value = None
        elif model is Site:
            q.filter.return_value.first.return_value = s
        elif model is Outreach:
            q.filter.return_value.first.return_value = None
        elif model is Job:
            q.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        else:
            q.filter.return_value.first.return_value = None
        return q

    mock_session.query.side_effect = _query_side_effect

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get(f"/api/businesses/{biz_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Biz With Site"
        assert data["site"] is not None
        assert data["site"]["review_status"] == "pending"
        assert data["site"]["template_used"] == "plumber"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_get_business_not_found():
    mock_session = _mock_db()
    mock_session.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get(f"/api/businesses/{uuid.uuid4()}")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /api/businesses/{id}/approve
# ---------------------------------------------------------------------------

def test_approve_business_enqueues_outreach():
    biz_id = uuid.uuid4()
    site_id = uuid.uuid4()
    b = _make_business(id=biz_id)
    s = _make_site(id=site_id, business_id=biz_id, review_status="pending")

    mock_session = _mock_db()
    # query(Business).filter().first() → b
    # query(Site).filter().first() → s
    # query(Outreach).filter().filter().first() → None (not sent yet)
    call_results = [b, s, None]
    call_iter = iter(call_results)

    def side_effect_first():
        return next(call_iter)

    mock_session.query.return_value.filter.return_value.first.side_effect = side_effect_first
    mock_session.query.return_value.filter.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        # The handler imports outreach_task lazily; patch .delay on the actual task object.
        with patch("app.workers.outreach_worker.outreach_task.delay") as mock_delay:
            resp = client.post(f"/api/businesses/{biz_id}/approve")
        assert resp.status_code == 200
        assert resp.json()["approved"] is True
        mock_delay.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_approve_business_not_found():
    mock_session = _mock_db()
    mock_session.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.post(f"/api/businesses/{uuid.uuid4()}/approve")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /api/businesses/{id}/reject
# ---------------------------------------------------------------------------

def test_reject_business():
    biz_id = uuid.uuid4()
    b = _make_business(id=biz_id)
    s = _make_site(business_id=biz_id, review_status="pending")

    mock_session = _mock_db()
    results = iter([b, s])
    mock_session.query.return_value.filter.return_value.first.side_effect = lambda: next(results)

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.post(f"/api/businesses/{biz_id}/reject")
        assert resp.status_code == 200
        assert resp.json()["rejected"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /api/businesses/{id}/retry
# ---------------------------------------------------------------------------

def test_retry_step_gather():
    biz_id = uuid.uuid4()
    b = _make_business(id=biz_id)

    mock_session = _mock_db()
    mock_session.query.return_value.filter.return_value.first.return_value = b

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        # Handler imports gather_task lazily; patch .delay on the actual task object.
        with patch("app.workers.gather.gather_task.delay") as mock_delay:
            resp = client.post(
                f"/api/businesses/{biz_id}/retry",
                json={"step": "gather"},
            )
        assert resp.status_code == 200
        assert resp.json()["queued"] is True
        assert resp.json()["step"] == "gather"
        mock_delay.assert_called_once_with(str(biz_id))
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_retry_step_unknown():
    biz_id = uuid.uuid4()
    b = _make_business(id=biz_id)

    mock_session = _mock_db()
    mock_session.query.return_value.filter.return_value.first.return_value = b

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.post(
            f"/api/businesses/{biz_id}/retry",
            json={"step": "invalid_step"},
        )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_retry_business_not_found():
    mock_session = _mock_db()
    mock_session.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.post(
            f"/api/businesses/{uuid.uuid4()}/retry",
            json={"step": "gather"},
        )
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /api/pipeline/run
# ---------------------------------------------------------------------------

def test_run_pipeline_queues_task():
    # discover_task is imported lazily inside the handler; patch .delay on the actual object.
    with patch("app.workers.discover.discover_task.delay") as mock_delay:
        resp = client.post(
            "/api/pipeline/run",
            json={"region": "Toronto, ON", "categories": ["plumber"]},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["queued"] is True
    assert data["region"] == "Toronto, ON"
    assert data["categories"] == ["plumber"]
    mock_delay.assert_called_once_with("Toronto, ON", ["plumber"])


def test_run_pipeline_missing_region():
    resp = client.post(
        "/api/pipeline/run",
        json={"categories": ["plumber"]},
    )
    # Pydantic validation will catch the missing required field
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/jobs
# ---------------------------------------------------------------------------

def test_list_jobs_empty():
    mock_session = _mock_db()
    mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
    mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_jobs_returns_data():
    j = _make_job(step="gather", status="success")

    mock_session = _mock_db()
    mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = [j]
    mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [j]

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["step"] == "gather"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_jobs_filter_by_status():
    j = _make_job(status="failed")

    mock_session = _mock_db()
    mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [j]

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get("/api/jobs?status=failed")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "failed"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# GET /api/settings
# ---------------------------------------------------------------------------

def test_get_settings():
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "review_mode" in data
    assert "outreach_daily_cap" in data
    assert "agency_domain" in data


def test_patch_settings():
    resp = client.patch(
        "/api/settings",
        json={"review_mode": False, "outreach_daily_cap": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["review_mode"] is False
    assert data["outreach_daily_cap"] == 5


def test_patch_settings_partial():
    """Patching only one field leaves the other unchanged."""
    # First set a known state
    client.patch("/api/settings", json={"outreach_daily_cap": 10})
    resp = client.patch("/api/settings", json={"review_mode": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["review_mode"] is True
    assert data["outreach_daily_cap"] == 10


# ---------------------------------------------------------------------------
# GET /api/sites
# ---------------------------------------------------------------------------

def test_list_sites_empty():
    mock_session = _mock_db()
    mock_session.query.return_value.order_by.return_value.all.return_value = []

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get("/api/sites")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_sites_returns_data():
    s = _make_site(template_used="plumber", review_status="pending")

    mock_session = _mock_db()
    mock_session.query.return_value.order_by.return_value.all.return_value = [s]

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get("/api/sites")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["template_used"] == "plumber"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /api/sites/{id}/approve
# ---------------------------------------------------------------------------

def test_approve_site_enqueues_outreach():
    biz_id = uuid.uuid4()
    site_id = uuid.uuid4()
    s = _make_site(id=site_id, business_id=biz_id, review_status="pending")

    mock_session = _mock_db()

    def _query_side_effect(model):
        from app.models.site import Site as SiteModel
        from app.models.outreach import Outreach as OutreachModel

        q = MagicMock()
        if model is SiteModel:
            q.filter.return_value.first.return_value = s
        elif model is OutreachModel:
            # Outreach idempotency guard: not sent yet → None
            q.filter.return_value.first.return_value = None
        else:
            q.filter.return_value.first.return_value = None
        return q

    mock_session.query.side_effect = _query_side_effect

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        # Handler imports outreach_task lazily; patch .delay on the actual task object.
        with patch("app.workers.outreach_worker.outreach_task.delay") as mock_delay:
            resp = client.post(f"/api/sites/{site_id}/approve")
        assert resp.status_code == 200
        assert resp.json()["approved"] is True
        mock_delay.assert_called_once_with(str(biz_id), str(site_id))
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_approve_site_not_found():
    mock_session = _mock_db()
    mock_session.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.post(f"/api/sites/{uuid.uuid4()}/approve")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /api/sites/{id}/reject
# ---------------------------------------------------------------------------

def test_reject_site():
    site_id = uuid.uuid4()
    s = _make_site(id=site_id, review_status="pending")

    mock_session = _mock_db()
    mock_session.query.return_value.filter.return_value.first.return_value = s

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.post(f"/api/sites/{site_id}/reject")
        assert resp.status_code == 200
        assert resp.json()["rejected"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# GET /api/outreach
# ---------------------------------------------------------------------------

def test_list_outreach_empty():
    mock_session = _mock_db()
    mock_session.query.return_value.order_by.return_value.all.return_value = []

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get("/api/outreach")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_outreach_returns_data():
    o = _make_outreach(email_status="sent")

    mock_session = _mock_db()
    mock_session.query.return_value.order_by.return_value.all.return_value = [o]

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        resp = client.get("/api/outreach")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["email_status"] == "sent"
    finally:
        app.dependency_overrides.pop(get_db, None)
